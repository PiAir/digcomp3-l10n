#!/usr/bin/env python3
import re
from pathlib import Path

def parse_authors(author_str):
    # RIS wants AU  - Lastname, Firstname or Lastname, F.
    # The input is often "Lastname, F., Lastname2, F. & Lastname3, F."
    # Strip unnecessary tags
    author_str = re.sub(r'\(Eds\.?\)|\(editors\)|\(authors\)|with |editors|authors|Ed\.', '', author_str, flags=re.IGNORECASE)
    
    # Split by common separators: " & ", " and ", "; "
    # But wait, "," is also a separator between different authors if they are "Lastname, F."
    # A common pattern is "Lastname, F. I.," or "Lastname, F.,"
    
    # Heuristic: split by " & ", " and ", "; "
    raw_parts = re.split(r' \& | and |; ', author_str)
    
    authors = []
    for part in raw_parts:
        part = part.strip()
        if not part: continue
        
        # If there are multiple commas, it might be "Lastname1, F1, Lastname2, F2"
        # Often after "F." there is a comma.
        # "Abendroth-Dias, K., Arias-Cabarcos, P., Bacco, F.M., Bassani, E., Bertoletti, A.,"
        sub_parts = re.split(r'(?<=\.\w)\s*,\s*|(?<=\w\.)\s*,\s*', part)
        if len(sub_parts) == 1:
            # Maybe just one author or comma-separated list without periods
            # Look for "Lastname, F"
            if "," in part:
                 authors.append(part.rstrip(','))
            else:
                 authors.append(part)
        else:
            for sp in sub_parts:
                if sp.strip():
                    authors.append(sp.strip().rstrip(','))
                    
    return [a for a in authors if len(a) > 1]

def convert_text_to_ris(input_file, output_file):
    text_raw = Path(input_file).read_text(encoding='utf-8')
    # Pre-process: fix URLs split by spaces/newlines
    # Heuristic: find http... and remove spaces until next punctuation or space following a non-URL char
    # Actually simpler: join lines first, then find URLs and remove spaces in them
    
    entries_raw = [e.strip() for e in text_raw.split('\n\n') if e.strip()]
    
    ris_entries = []
    
    for entry in entries_raw:
        # Join lines but avoid merging words across line breaks incorrectly
        # If a line ends with a hyphen, merge. Otherwise space.
        lines = entry.splitlines()
        content = ""
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            if content.endswith('-'):
                content = content[:-1] + line
            else:
                if content: content += " "
                content += line
        
        # Fix URLs that might have spaces in them from the original text's formatting
        # This is tricky without breaking the rest. 
        # Pattern: find http and the next few words that look like URL parts
        def fix_url(m):
            return m.group(0).replace(" ", "")
        content = re.sub(r'https?://\S+(?:\s+\S+)*', fix_url, content)
        # Often the space is after a slash or dot in the URL
        content = re.sub(r'(https?://[^\s]+)\s+([^\s\.]+\.[^\s]+)', r'\1\2', content)

        # Heuristic Regex
        match = re.match(r'^(.*?)\s+\((\d{4}[a-z]?)\)\.?\s+(.*?)$', content)
        if not match:
            continue
            
        authors_raw, year, rest = match.groups()
        authors = parse_authors(authors_raw)
        
        # Link extraction
        link_match = re.search(r'(https?://\S+|doi:\s*\S+)', rest)
        link = link_match.group(0) if link_match else ""
        text_before_link = rest[:link_match.start()].strip() if link_match else rest.strip()
        
        # Type and extra info
        entry_type = "RPRT"
        title = text_before_link
        secondary_title = ""
        volume = ""
        issue = ""
        pages = ""
        publisher = ""
        city = ""
        
        # Journal detection: "Journal Title, Vol(Issue), Pages"
        journal_match = re.search(r'^(.*?)\.\s+([A-Za-z\s]+),\s*(\d+)\s*(\(\d+\))?,\s*([\d\-\u2013]+)', text_before_link)
        if journal_match:
            entry_type = "JOUR"
            title, secondary_title, volume, issue, pages = journal_match.groups()
            issue = issue.strip('()') if issue else ""
        else:
            # Report or Book
            # Check for "City: Publisher" at the end of text_before_link
            pub_match = re.search(r'^(.*?)\.\s+([^:]+):\s+(.*?)$', text_before_link)
            if pub_match:
                title, city, publisher = pub_match.groups()
            else:
                # Basic split
                parts = text_before_link.rsplit('. ', 1)
                if len(parts) > 1:
                    title, publisher = parts
        
        # Build RIS
        res = []
        res.append(f"TY  - {entry_type}")
        for au in authors:
            res.append(f"AU  - {au}")
        
        # Split year and optional suffix (e.g., 2024a -> 2024, a)
        year_match = re.match(r'^(\d{4})([a-z])?$', year)
        if year_match:
            base_year, suffix = year_match.groups()
            res.append(f"PY  - {base_year}")
            if suffix:
                res.append(f"N1  - Year Suffix: {suffix}")
        else:
            res.append(f"PY  - {year}")

        res.append(f"TI  - {title.strip('.')}")
        if secondary_title:
            res.append(f"T2  - {secondary_title.strip()}")
        if volume:
            res.append(f"VL  - {volume}")
        if issue:
            res.append(f"IS  - {issue}")
        if pages:
            res.append(f"SP  - {pages}")
        if publisher:
            res.append(f"PB  - {publisher.strip()}")
        if city:
            res.append(f"CY  - {city.strip()}")
        if link:
            # Standardize Link
            link = link.strip(').')
            if "doi.org" in link or link.startswith("10."):
                doi = link.split("doi.org/")[-1]
                res.append(f"DO  - {doi}")
            res.append(f"UR  - {link}")
        res.append("ER  - ")
        ris_entries.append("\n".join(res))
        
    Path(output_file).write_text("\n\n".join(ris_entries), encoding='utf-8')
    return len(ris_entries)

if __name__ == "__main__":
    count = convert_text_to_ris(
        "d:/Temp/Python/weblate/digcomp3-l10n/sources/references.txt",
        "d:/Temp/Python/weblate/digcomp3-l10n/sources/references.ris"
    )
    print(f"Successfully converted {count} references to RIS.")
