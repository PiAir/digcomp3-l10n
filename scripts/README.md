# 1) Nieuwe digcomp3-l10n repo aanmaken uit XLSX + JSON-LD + DOCX

## A. Basis repo + normatieve CSV’s (XLSX → locale/*)

Gebruik: ```build_digcomp_weblate_repo_steps_v3.py``` (repo/locale structuur + core CSV’s + (basis) manifest)

Commando (vanuit je hoofdmap, waar XLSX/DOCX staan):
```
python build_digcomp_weblate_repo_steps_v3.py step1 --xlsx "DigComp 3.0 Data Supplement 24 Nov 2025.xlsx" --repo-root .
```

Dit maakt/actualiseert:
```
.\digcomp3-l10n\locale\core-framework\en.csv + nl.csv
.\digcomp3-l10n\locale\levels\en.csv + nl.csv
.\digcomp3-l10n\locale\statements\en.csv + nl.csv
.\digcomp3-l10n\locale\outcomes\en.csv + nl.csv
.\digcomp3-l10n\locale\glossary\en.csv + nl.csv
```
en (afhankelijk van versie) ```.\digcomp3-l10n\manifest.json``` of een voorzet ervoor

## B. Texts uit Worddocument extraheren (DOCX → locale/texts)
Gebruik (laatste en beste voor jouw situatie met headings en betere blokindeling):
```extract_texts_hashed_v3.py``` (of als je expliciet NL wilt behouden uit een oudere dump: ```extract_texts_structural_preserve.py```)

Normale extract (targets leeg, geschikt om daarna extern te vertalen):
```
python extract_texts_hashed_v3.py --docx "DigComp 3.0 EDITABLE 16 Dec 2025 - bewerkt.docx" --repo-root . --max-len 3000
```
Als je juist een bestaande NL wilt "meepakken" uit een oudere nl.csv (preserve):
```
python extract_texts_structural_preserve.py --docx "DigComp 3.0 EDITABLE 16 Dec 2025 - bewerkt.docx" --repo-root . --max-len 3000 --preserve-nl-csv "digcomp3-l10n\locale\texts\nl_old_translated.csv"
```
Resultaat:
```
.\digcomp3-l10n\locale\texts\en.csv
.\digcomp3-l10n\locale\texts\nl.csv
```
## C. Repo naar GitHub / Weblate

Vervolgens (globaal):
```
cd digcomp3-l10n
git init
git add .
git commit -m "Initial DigComp 3.0 localization repo"
git remote add origin <jouw github repo url>
git push -u origin main
```

# 2) Uit vertaalde nl.csv bestanden weer XLSX + JSON-LD + DOCX genereren

## A. XLSX + JSON-LD bouwen
Gebruik:
```build_digcomp_nl_artifacts_v3.py```

Voorbeeld (output naar .\nl\):
```
python build_digcomp_nl_artifacts_v3.py --repo-root . --out-dir .\nl --xlsx --jsonld
```

## B. DOCX bouwen
Gebruik (laatste die bedoeld is om uit locale/texts/nl.csv de Word te vullen):
```build_digcomp_docx_from_locale_v5.py```
(dit is de versie die we maakten na de sanity-check ronde)

Voorbeeld:
```
python build_digcomp_docx_from_locale_v5.py --repo-root . --docx-in "DigComp 3.0 EDITABLE 16 Dec 2025 - bewerkt.docx" --docx-out ".\nl\DigComp_3.0_nl.docx"
```
Belangrijk: deze stap is afhankelijk van hoe goed jouw texts-extract de paragrafen/tabellen "matcht" op basis van location/context/source. Met jouw opgeschoonde Word en extract_texts_hashed_v3.py/extract_texts_structural_preserve.py is dit in de praktijk het meest robuuste pad.

# Praktische "meest gebruikte" workflow in 6 regels

## Repo bouwen:
```
python build_digcomp_weblate_repo_steps_v3.py step1 --xlsx "DigComp 3.0 Data Supplement 24 Nov 2025.xlsx" --repo-root .
python extract_texts_hashed_v3.py --docx "DigComp 3.0 EDITABLE 16 Dec 2025 - bewerkt.docx" --repo-root . --max-len 3000
```
## Na vertalen (Weblate / extern):
```
python build_digcomp_nl_artifacts_v3.py --repo-root . --out-dir .\nl --xlsx --jsonld
python build_digcomp_docx_from_locale_v5.py --repo-root . --docx-in "DigComp 3.0 EDITABLE 16 Dec 2025 - bewerkt.docx" --docx-out ".\nl\DigComp_3.0_nl.docx"
```
