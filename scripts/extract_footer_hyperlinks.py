import fitz  # PyMuPDF
import pandas as pd
import argparse
import os
import re
import csv

def extract_data(pdf_path, output_dir):
    if not os.path.exists(pdf_path):
        print(f"Fout: Bestand {pdf_path} niet gevonden.")
        return

    doc = fitz.open(pdf_path)
    footers_dict = {} 
    hyperlinks_data = []
    seen_links = set()
    
    current_section = "Inleiding"

    for page_num in range(len(doc)):
        page = doc[page_num]
        display_page_num = page_num + 1
        blocks = page.get_text("blocks")
        # Sorteer blokken op verticale positie
        blocks.sort(key=lambda b: b[1])
        page_height = page.rect.height
        
        # 1. Context Bepaling (Headers)
        for b in blocks:
            if b[1] < 100:
                txt = b[4].strip()
                # Negeer de standaard header "DigComp 3.0" en paginanummers
                if txt and txt != "DigComp 3.0" and not txt.isdigit() and len(txt) > 5:
                    current_section = txt.split('\n')[0].strip()
                    break

        # 2. Voetteksten extraheren
        # Verzamel alle tekst in de onderste regio van de pagina
        footer_zone_text = ""
        for b in blocks:
            if b[1] > (page_height - 180):
                # Filter herhalende elementen die geen voetnoot zijn
                if b[4].strip() == "DigComp 3.0" or b[4].strip().isdigit():
                    continue
                footer_zone_text += "\n" + b[4]

        # De split-logica: zoek naar getal (1-12) aan het begin van een regel
        # (?m) = multiline mode, zodat ^ matcht na elke newline
        parts = re.split(r'(?m)^([1-9]|1[0-2])\.\s+', footer_zone_text)
        
        if len(parts) > 1:
            for i in range(1, len(parts), 2):
                f_num = int(parts[i])
                f_content = parts[i+1].strip()
                
                if f_content:
                    # Vervang newlines door spaties voor een vloeiende zin
                    clean_content = " ".join(f_content.replace('\n', ' ').split())
                    
                    if f_num not in footers_dict:
                        footers_dict[f_num] = {
                            "locations": f"footer_{f_num}",
                            "context": current_section,
                            "source": clean_content,
                            "target": ""
                        }
                    else:
                        # Voeg toe aan bestaande (voor voetnoten die doorlopen)
                        footers_dict[f_num]["source"] += " " + clean_content

        # 3. Hyperlinks extraheren
        links = page.get_links()
        for link in links:
            if "uri" in link:
                url = link["uri"]
                link_rect = link["from"]
                context_paragraph = "Context niet gevonden"
                for block in blocks:
                    if (block[0] <= link_rect[0] <= block[2] and 
                        block[1] <= link_rect[1] <= block[3]):
                        context_paragraph = block[4].replace('\n', ' ').strip()
                        break
                
                link_id = (display_page_num, context_paragraph, url)
                if link_id not in seen_links:
                    hyperlinks_data.append({
                        "locations": f"Pagina {display_page_num}",
                        "context": context_paragraph,
                        "source": url,
                        "target": ""
                    })
                    seen_links.add(link_id)

    # Finaliseer voetnoten en sorteer op nummer
    final_footers = [footers_dict[k] for k in sorted(footers_dict.keys())]

    # Schrijf naar CSV met correcte aanhalingstekens
    pd.DataFrame(final_footers).to_csv(os.path.join(output_dir, "footers.csv"), 
                                      index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
    pd.DataFrame(hyperlinks_data).to_csv(os.path.join(output_dir, "hyperlinks.csv"), 
                                        index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)

    print(f"Klaar! Er zijn {len(final_footers)} voetnoten en {len(hyperlinks_data)} hyperlinks gevonden.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="DigComp3.0.pdf")
    parser.add_argument("--output", default=".")
    args = parser.parse_args()
    
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        
    extract_data(args.input, args.output)