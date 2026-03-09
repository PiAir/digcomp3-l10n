# Scripts

##  Create new repo based on XLSX
Basic repo + normatieve CSV’s (XLSX → locale/*)
Use python scripts\build_digcomp_weblate_repo_steps.py step1 --xlsx "sources\DigComp 3.0 Data Supplement 24 Nov 2025.xlsx"

This creates/updates:
.\digcomp3-l10n\locale\core-framework\en.csv + nl.csv
.\digcomp3-l10n\locale\levels\en.csv + nl.csv
.\digcomp3-l10n\locale\statements\en.csv + nl.csv
.\digcomp3-l10n\locale\outcomes\en.csv + nl.csv
.\digcomp3-l10n\locale\glossary\en.csv + nl.csv

** don't use the Texts from Worddocument extraction option (DOCX → locale/texts), it works, but the route via .ODT (using 
```"D:\LibreOffice\App\libreoffice\program\soffice.exe" --headless --convert-to odt --outdir D:\Temp\Python\weblate\work "D:\Temp\Python\weblate\DigComp 3.0 engels opgeschoond.docx"``` works better.

## Repo to GitHub / Weblate
```bash
cd digcomp3-l10n
git init
git add .
git commit -m "Initial DigComp 3.0 localization repo"
git remote add origin <your github repo url>
git push -u origin main
```

## Weblate update
To pull new updates from Weblate:
```bash
git pull origin main
```

## Update XLSX + JSON-LD based on translated .csv files
Use: `.\scripts\build_digcomp_nl_artifacts.py`
(Note: script name was updated from `build_digcomp_nl_artifacts_v3.py`)

For example:
```bash
python .\scripts\build_digcomp_nl_artifacts.py --repo-root . --out-dir .\nl --xlsx --jsonld
```

## Extract hyperlinks and footers from source pdf
Use: `.\scripts\extract_footer_hyperlinks.py` (rarely used but still available)

For example:
```bash
python .\scripts\extract_footer_hyperlinks.py --input "JRC144121_01.pdf" --output ".\tables"
```

## Create table documents
Use: `.\scripts\extract_tables.py`
For example:
```bash
# Extract glossary for NL (no heading, no BRON column)
python .\scripts\extract_tables.py glossary --lang nl

# Extract acronyms
python .\scripts\extract_tables.py acronyms --lang nl --output acroniemen_nl.docx
python .\scripts\extract_tables.py acronyms --lang en --output acronyms_en.docx
```
*Note: you need the translated JSON-LD for some of the conversions to work, so do that first.*

## Generate docx from qmd
To generate the full document from Quarto and consolidate tables:
```bash
# Render the QMD to DOCX
quarto render qmd\DigComp3.0-Nederlands.qmd --to docx

# Use the R script to finish/consolidate the document
Rscript scripts\finish_document.R
```
