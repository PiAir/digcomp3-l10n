import pandas as pd
import json
import argparse
import os
import re

# --- CONFIGURATIE EN KLEUREN ---
COLOR_MAP = {
    "CompetenceArea/1": ["FFF2CC", "FFE699", "FFD966", "FFC000"], # Goud/Geel
    "CompetenceArea/2": ["D9E1F2", "B4C6E7", "8EA9DB", "2F5597"], # Blauw
    "CompetenceArea/3": ["FBE5D6", "F8CBAD", "F4B084", "ED7D31"], # Oranje
    "CompetenceArea/4": ["E2EFDA", "C6E0B4", "A9D08E", "70AD47"], # Groen
    "CompetenceArea/5": ["FCE4D6", "F9CB9C", "F4B084", "E26B67"], # Rood/Coral
    "Standard": "1F4E78" 
}

AREA_COLORS = {k: v[3] for k, v in COLOR_MAP.items() if k != "Standard"}

def format_ai_label(label_raw, lang):
    """Zet de ruwe AI label tekst om naar voluit geschreven varianten."""
    if not label_raw or "not Implicit" in label_raw or label_raw == "-":
        return "-"
    if lang == "nl":
        return label_raw.replace('AI-Implicit', 'AI-Impliciet').replace('AI-Explicit', 'AI-Expliciet')
    return label_raw

# --- QMD HELPERS ---

def make_flextable_chunk(df_json_str, col_widths=None, header_bg=None, header_text_color="black"):
    """Genereert een R chunk met Flextable om een Docx tabel te maken."""
    chunk = [
        "```{r}",
        "#| echo: false",
        "#| message: false",
        "#| warning: false",
        "library(jsonlite)",
        "library(flextable)",
        "library(dplyr)",
        "library(ftExtra)",
        f'json_data <- r"----[\n{df_json_str}\n]----"',
        "df <- jsonlite::fromJSON(json_data)",
        # We filteren de meta-kolommen eruit
        "disp_cols <- names(df)[!names(df) %in% c('BgColorRow', 'BgColor1', 'BgColor2', 'TextColor1', 'TextColor2', 'ImagePath')]",
        "ft <- flextable(df[, disp_cols, drop=FALSE])",
        "ft <- colformat_md(ft, j = disp_cols)",
        "ft <- theme_box(ft)",
        'ft <- align(ft, align = "left", part = "all")',
        'ft <- valign(ft, valign = "top", part = "body")'
    ]
    
    # Header styling
    if header_bg:
        chunk.append(f'ft <- bg(ft, bg = "#{header_bg}", part = "header")')
        chunk.append(f'ft <- color(ft, color = "{header_text_color}", part = "header")')
    else:
        # Standaard header (zoals in referentie: wit/leeg)
        chunk.append('ft <- bg(ft, bg = "white", part = "header")')
        chunk.append('ft <- color(ft, color = "black", part = "header")')
        chunk.append('ft <- bold(ft, part = "header")')
    
    chunk.extend([
        "for (i in seq_len(nrow(df))) {",
        # Hele rij kleur
        "  if ('BgColorRow' %in% names(df) && !is.na(df$BgColorRow[i]) && df$BgColorRow[i] != '') {",
        "    ft <- bg(ft, i = i, bg = paste0('#', df$BgColorRow[i]), part = 'body')",
        "  }",
        # Kolom 1 kleur
        "  if ('BgColor1' %in% names(df) && !is.na(df$BgColor1[i]) && df$BgColor1[i] != '') {",
        "    ft <- bg(ft, i = i, j = 1, bg = paste0('#', df$BgColor1[i]), part = 'body')",
        "  }",
        # Kolom 2 kleur (Cruciaal voor DigComp3 referentie!)
        "  if ('BgColor2' %in% names(df) && !is.na(df$BgColor2[i]) && df$BgColor2[i] != '') {",
        "    ft <- bg(ft, i = i, j = 2, bg = paste0('#', df$BgColor2[i]), part = 'body')",
        "  }",
        "  if ('TextColor1' %in% names(df) && !is.na(df$TextColor1[i]) && df$TextColor1[i] != '') {",
        "    ft <- color(ft, i = i, j = 1, color = paste0('#', df$TextColor1[i]), part = 'body')",
        "  }",
        "}",
        "if ('Info' %in% names(df)) ft <- merge_v(ft, j = 1)",
        "if ('GEBIED' %in% names(df)) ft <- merge_v(ft, j = 1)",
        "if ('AREA' %in% names(df)) ft <- merge_v(ft, j = 1)"
    ])

    if col_widths:
        for j, w in enumerate(col_widths):
            chunk.append(f"ft <- width(ft, j = {j+1}, width = {w})")
    else:
        chunk.append("ft <- autofit(ft)")
        
    chunk.append("ft")
    chunk.append("```")
    return "\n".join(chunk)

# --- GENERATIE FUNCTIES ---

def generate_digcomp3(json_path, lang, output_path, images_path):
    """Genereert de gedetailleerde 3.2 competentiepagina's als QMD."""
    with open(json_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)["@graph"]
    
    areas = sorted([i for i in graph if i["@type"] == "CompetenceArea"], key=lambda x: x["@id"])
    competences = [i for i in graph if i["@type"] == "Competence"]
    levels = [i for i in graph if i["@type"] == "ProficiencyLevel"]
    statements = [i for i in graph if i["@type"] == "CompetenceStatement"]
    suffix = "_nl" if lang == "nl" else ""
    
    qmd_output = []
    
    for area in areas:
        area_id = area["@id"]
        area_num = area_id.split("/")[-1]
        area_name = area.get(f"name{suffix}", area.get("name", "Unknown Area"))
        # De 4 tinten voor de 4 niveaus
        tints = COLOR_MAP.get(area_id, ["FFFFFF"]*4)
        
        for comp in sorted([c for c in competences if c["competence_area_id"] == area_id], key=lambda x: x["@id"]):
            comp_id_short = comp["@id"].split("/")[-1]
            comp_name = comp.get(f"name{suffix}", comp.get("name", "Unknown Competence"))
            comp_desc = comp.get(f"description{suffix}", comp.get("description", ""))
            
            qmd_output.append(f"## {comp_id_short} {comp_name}\n")
            
            img_filename = f"DC3_{comp_id_short.replace('.', 'p')}.png"
            abs_img_path = os.path.abspath(os.path.join(images_path, img_filename)).replace("\\", "/")
            if os.path.exists(os.path.join(images_path, img_filename)):
                qmd_output.append(f"![]({abs_img_path}){{width=3.0cm}}\n")
            
            rows = []
            info_text = f"**{area_num}. {area_name.upper()}**\n\n**{comp_id_short} {comp_name}**\n\n{comp_desc}"
            
            for idx, lv_key in enumerate(["Basic", "Intermediate", "Advanced", "Highly advanced"]):
                lv_name = next((l.get(f"four_levels_name{suffix}", l.get("four_levels_name", lv_key)) for l in levels if lv_key in l["@id"]), lv_key)
                lv_display = f"*Op {lv_name.lower()} niveau kunnen individuen*" if lang == "nl" else f"*At {lv_name.lower()} level, individuals*"
                
                relevant = [s for s in statements if s["competence_id"] == comp["@id"] and s["four_levels_proficiency_name"].startswith(f"ProficiencyLevel/{lv_key}")]
                stmt_text = []
                for s in relevant:
                    ai = format_ai_label(s.get('ai_label', ''), lang)
                    stmt_desc = s.get(f"description{suffix}", s.get("description", ""))
                    stmt_text.append(f"**{s['@id'].split('/')[-1]}**: {stmt_desc} [{ai}]")
                
                rows.append({
                    "Info": info_text if idx == 0 else "",
                    "Niveau": lv_display,
                    "Beschrijving": "\n".join(stmt_text),
                    # In referentie is de TWEEDE kolom (Niveau) gekleurd!
                    "BgColor2": tints[idx], 
                    "TextColor1": "000000"
                })
            
            df_json_str = json.dumps(rows, ensure_ascii=False)
            # 3-kolom layout: Info (merged), Niveau (gekleurd), Beschrijving
            qmd_output.append(make_flextable_chunk(df_json_str, col_widths=[2.0, 1.4, 3.2], header_bg=None))
            qmd_output.append("\n")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(qmd_output))

def generate_table2(json_path, lang, output_path, images_path):
    """Genereert Tabel 2: Overzicht van gebieden en competenties."""
    with open(json_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)["@graph"]
    areas = sorted([i for i in graph if i["@type"] == "CompetenceArea"], key=lambda x: x["@id"])
    competences = [i for i in graph if i["@type"] == "Competence"]
    suffix = "_nl" if lang == "nl" else ""
    
    qmd_output = [f"# {'Tabel 2' if lang == 'nl' else 'Table 2'}\n"]
    headers = ["GEBIED", "TITEL", "BESCHRIJVING"] if lang == "nl" else ["AREA", "TITLE", "DESCRIPTOR"]
    
    rows = []
    for area in areas:
        area_id = area["@id"]
        area_num = area_id.split("/")[-1]
        area_name = area.get(f"name{suffix}", area.get("name", "Unknown Area")).upper()
        area_desc = area.get(f"description{suffix}", area.get("description", ""))
        area_comps = sorted([c for c in competences if c["competence_area_id"] == area_id], key=lambda x: x["@id"])
        
        # Referentie: GEBIED kolom heeft een achtergrondkleur, TITEL/BESCHR wit.
        color_hex = AREA_COLORS.get(area_id, "1F4E78")
        
        img_filename = f"DC3_small_c{area_num}.png"
        abs_img_path = os.path.abspath(os.path.join(images_path, img_filename)).replace("\\", "/")
        img_md = f"![]({abs_img_path}){{width=1.5cm}}" if os.path.exists(os.path.join(images_path, img_filename)) else ""
        
        info_text = f"{img_md}\n\n**{area_num}. {area_name}**\n\n{area_desc}"
        
        for i, comp in enumerate(area_comps):
            comp_name = comp.get(f"name{suffix}", comp.get("name", ""))
            comp_desc = comp.get(f"description{suffix}", comp.get("description", ""))
            rows.append({
                headers[0]: info_text if i == 0 else "",
                headers[1]: f"**{comp['@id'].split('/')[-1]} {comp_name}**",
                headers[2]: comp_desc,
                "BgColor1": color_hex if i == 0 else "", # Alleen de Info-kolom heeft de kleur
                "TextColor1": "FFFFFF" if i == 0 else "000000"
            })
            
    df_json_str = json.dumps(rows, ensure_ascii=False)
    # Referentie: Witte header met zwarte tekst.
    qmd_output.append(make_flextable_chunk(df_json_str, col_widths=[1.8, 1.4, 3.2]))
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(qmd_output))

def generate_csv_output(csv_path, type_name, lang, output_path):
    """Verwerkt Acronyms of Glossary vanuit Weblate CSV export."""
    df = pd.read_csv(csv_path, encoding='utf-8-sig').fillna('')
    grouped = {}
    content_idx = 3 if lang == "nl" else 2
    
    if type_name == "acronyms":
        pattern = re.compile(r"digcomp\.acronym\.([^.]+)\.(label|expansion)")
        for _, row in df.iterrows():
            key, val = str(row.iloc[0]), str(row.iloc[content_idx])
            match = pattern.search(key)
            if match:
                id_str, field = match.group(1), match.group(2)
                if id_str not in grouped: grouped[id_str] = {'id': id_str.upper(), 'val': ''}
                if field == 'label': grouped[id_str]['id'] = val
                elif field == 'expansion': grouped[id_str]['val'] = val
        data = sorted(grouped.values(), key=lambda x: str(x['id']).lower())
        headers = ["ACRONIEM", "BETEKENIS"] if lang == "nl" else ["ACRONYM", "EXPANSION"]
        rows = [{headers[0]: i['id'], headers[1]: i['val']} for i in data]
        widths = [1.5, 4.5]
    else: # glossary
        pattern = re.compile(r"digcomp\.glossary\.([^.]+)\.(label|definition|source)")
        for _, row in df.iterrows():
            key, val = str(row.iloc[0]), str(row.iloc[content_idx])
            match = pattern.search(key)
            if match:
                id_str, field = match.group(1), match.group(2)
                if id_str not in grouped: grouped[id_str] = {'term': '', 'def': '', 'src': ''}
                if field == 'label': grouped[id_str]['term'] = val
                elif field == 'definition': grouped[id_str]['def'] = val
                elif field == 'source': grouped[id_str]['src'] = val
        data = sorted(grouped.values(), key=lambda x: str(x['term']).lower())
        headers = ["TERM", "DEFINITIE", "BRON"] if lang == "nl" else ["TERM", "DEFINITION", "SOURCE"]
        rows = [{headers[0]: i['term'], headers[1]: i['def'], headers[2]: i['src']} for i in data]
        widths = [1.5, 3.5, 1.0]

    df_json_str = json.dumps(rows, ensure_ascii=False)
    title = "ACRONYMEN" if type_name == "acronyms" else "GLOSSARIUM"
    qmd_output = [f"# {title}\n"]
    # Schone header met blauwe achtergrond voor deze lijsten (zoals in referentie)
    qmd_output.append(make_flextable_chunk(df_json_str, col_widths=widths, header_bg="1F4E78", header_text_color="white"))
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(qmd_output))

def generate_outcomes(json_path, lang, output_path):
    """Genereert Learning Outcomes als QMD."""
    with open(json_path, 'r', encoding='utf-8') as f:
        graph = json.load(f)["@graph"]
    areas = sorted([i for i in graph if i["@type"] == "CompetenceArea"], key=lambda x: x["@id"])
    competences = [i for i in graph if i["@type"] == "Competence"]
    levels = [i for i in graph if i["@type"] == "ProficiencyLevel"]
    outcomes = [i for i in graph if i["@type"] == "LearningOutcome"]
    suffix = "_nl" if lang == "nl" else ""
    
    qmd_output = []
    
    for area in areas:
        area_id = area["@id"]
        color_hex = AREA_COLORS.get(area_id, "1F4E78")
        for comp in sorted([c for c in competences if c["competence_area_id"] == area_id], key=lambda x: x["@id"]):
            comp_id = comp["@id"]
            comp_num = comp_id.split("/")[-1]
            comp_name = comp.get(f"name{suffix}", comp.get("name", ""))
            
            qmd_output.append(f"### {comp_num} {comp_name}\n")
            
            headers = ["ID", "Leerresultaat", "Niveau", "K/V/H", "AI"] if lang == "nl" else ["ID", "Outcome", "Level", "K/S/A", "AI"]
            rows = []
            
            for o in sorted([o for o in outcomes if o["competence_id"] == comp_id], key=lambda x: x["@id"]):
                lv_name = next((l.get(f"four_levels_name{suffix}", l.get("four_levels_name", "Level")) for l in levels if o["four_levels_proficiency_name"] in l["@id"]), "Level")
                description = o.get(f"description{suffix}", o.get("description", ""))
                type_val = o.get("type", "").replace("Knowledge", "Kennis").replace("Skill", "Vaardigheid").replace("Attitude", "Houding") if lang == "nl" else o.get("type", "")
                rows.append({
                    headers[0]: o["@id"].split("/")[-1],
                    headers[1]: description,
                    headers[2]: lv_name,
                    headers[3]: type_val,
                    headers[4]: format_ai_label(o.get("ai_label", ""), lang)
                })
            
            df_json_str = json.dumps(rows, ensure_ascii=False)
            qmd_output.append(make_flextable_chunk(df_json_str, col_widths=[0.6, 3.0, 1.0, 0.8, 0.8], header_bg=color_hex, header_text_color="white"))
            qmd_output.append("\n")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(qmd_output))

# --- MAIN ---

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_path = os.path.normpath(os.path.join(script_dir, '..', 'locale'))
    default_json = os.path.normpath(os.path.join(script_dir, '..', '..', 'nl', 'DigComp_3.0_Data_Supplement_nl.jsonld'))
    default_images = os.path.normpath(os.path.join(script_dir, '..', 'images'))

    parser = argparse.ArgumentParser()
    parser.add_argument('type', choices=['acronyms', 'glossary', 'digcomp3', 'table2', 'outcomes'])
    parser.add_argument('--lang', choices=['en', 'nl'], default='nl')
    parser.add_argument('--path', default=default_path)
    parser.add_argument('--json', default=default_json)
    parser.add_argument('--images', default=default_images)
    parser.add_argument('--output', help='Output filename')
    args = parser.parse_args()

    out = args.output if args.output else f"DigComp3_{args.type}_{args.lang}.qmd"
    
    if args.type == 'outcomes': 
        generate_outcomes(args.json, args.lang, out)
    elif args.type == 'digcomp3': 
        generate_digcomp3(args.json, args.lang, out, args.images)
    elif args.type == 'table2': 
        generate_table2(args.json, args.lang, out, args.images)
    else:
        csv_path = os.path.join(args.path, args.type, f"{args.lang}.csv")
        generate_csv_output(csv_path, args.type, args.lang, out)
        
    print(f"Gereed: {out}")

if __name__ == "__main__":
    main()
