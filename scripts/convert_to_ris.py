#!/usr/bin/env python3
import re
from pathlib import Path

def parse_authors(author_str):
    # Strip unnecessary tags
    author_str = re.sub(r'\(Eds\.?\)|\(editors\)|\(authors\)|with |editors|authors|Ed\.', '', author_str, flags=re.IGNORECASE)
    
    # Heuristic for RIS AU tag: Lastname, Firstname
    # Split by common separators
    parts = re.split(r' \& | and |; ', author_str)
    
    final_authors = []
    for part in parts:
        part = part.strip()
        if not part or part.lower() in ["et al.", "et al"]:
            continue
            
        # Try to detect if it's "Lastname, F." or "Firstname Lastname"
        # If it has a comma, it's probably already swapped
        # But handle multiple authors grouped by comma incorrectly: "A, B, C, D"
        
        # Split by comma followed by space and another word starting with capital or initial
        # This is tricky. Let's use a simpler heuristic:
        # If there are many commas, and it's not "Lastname, F. I.," format
        commas = part.count(',')
        if commas > 1 and not re.search(r'[A-Z]\.\s*,', part):
            # Probably "Author 1, Author 2, Author 3" (unswapped)
            sub_parts = [s.strip() for s in part.split(',')]
            for sp in sub_parts:
                if sp: final_authors.append(sp)
        else:
            # Check for missing periods in "Lastname, F"
            # "Piña de Santisteban, P, Schulz, C."
            # Split manually if we see a space or comma after an initial without period
            sub_parts = re.split(r'(?<=,\s[A-ZA-Z]\b)\s*,\s*|(?<=,\s[A-ZA-Z]\.)\s*,\s*', part)
            if len(sub_parts) > 1:
                for sp in sub_parts:
                    if sp: final_authors.append(sp.strip().rstrip(','))
            else:
                 final_authors.append(part.rstrip(','))
                
    return [a.strip() for a in final_authors if len(a) > 1]

def convert_text_to_ris(input_file, output_file):
    raw_text = Path(input_file).read_text(encoding='utf-8')
    
    # Pre-clean
    lines = [line.strip() for line in raw_text.splitlines()]
    entries_blocks = []
    current_block = []
    for line in lines:
        if not line:
            if current_block:
                entries_blocks.append(" ".join(current_block))
                current_block = []
        else:
            current_block.append(line)
    if current_block:
        entries_blocks.append(" ".join(current_block))
    
    ris_entries = []
    for content in entries_blocks:
        match = re.match(r'^(.*?)\s+\((\d{4}[a-z]?)\)\.?\s+(.*?)$', content)
        if not match: continue
            
        authors_raw, year_raw, rest = match.groups()
        authors = parse_authors(authors_raw)
        
        link_match = re.search(r'(https?://\S+|doi:\s*\S+)', rest)
        link = link_match.group(0).strip(').') if link_match else ""
        text_before_link = rest[:link_match.start()].strip() if link_match else rest.strip()
        
        entry_type = "RPRT"
        title = text_before_link
        journal = ""
        volume = ""
        issue = ""
        pages = ""
        publisher = ""
        city = ""
        
        # Journal detection
        journal_match = re.search(r'^(.*?)\.\s+([A-Z][A-Za-z\s]+),\s*(\d+)\s*(\(\d+\))?,\s*([\d\-\u2013]+)$', text_before_link)
        if journal_match:
            entry_type = "JOUR"
            title, journal, volume, issue, pages = journal_match.groups()
            issue = issue.strip('()') if issue else ""
        else:
            pub_match = re.search(r'^(.*?)\.\s+([^:]+):\s+(.*?)$', text_before_link)
            if pub_match:
                title, city, publisher = pub_match.groups()
            else:
                parts = text_before_link.rsplit('. ', 1)
                if len(parts) > 1:
                    title, publisher = parts

        # Simplified Year
        year_match = re.search(r'(\d{4})', year_raw)
        year = year_match.group(1) if year_match else year_raw
        
        # Build RIS with Optimized Tag Order (PY near top)
        res = []
        res.append(f"TY  - {entry_type}")
        res.append(f"PY  - {year}")
        res.append(f"T1  - {title.strip('.')}")
        for au in authors:
            res.append(f"AU  - {au.strip('.')}")
        
        if journal: res.append(f"JF  - {journal.strip()}") # JF is often better than T2 for Mendeley
        if volume: res.append(f"VL  - {volume}")
        if issue: res.append(f"IS  - {issue}")
        if pages: res.append(f"SP  - {pages}")
        if publisher: res.append(f"PB  - {publisher.strip('.')}")
        if city: res.append(f"CY  - {city.strip()}")
        
        if link:
            if "doi.org" in link or "doi:" in link.lower():
                doi = link.split("doi.org/")[-1].replace("doi:", "").strip()
                res.append(f"DO  - {doi}")
            res.append(f"UR  - {link}")
            
        res.append("ER  - ")
        ris_entries.append("\n".join(res))
    
    # Use Windows Line Endings and UTF-8 with BOM
    output_path = Path(output_file)
    content = "\r\n".join(ris_entries) + "\r\n"
    # Write with UTF-8-SIG (BOM)
    output_path.write_text(content, encoding='utf-8-sig')
    return len(ris_entries)

if __name__ == "__main__":
    count = convert_text_to_ris(
        "d:/Temp/Python/weblate/digcomp3-l10n/sources/references.txt",
        "d:/Temp/Python/weblate/digcomp3-l10n/sources/references.ris"
    )
    print(f"Successfully converted {count} references to RIS.")
