# digcomp3-l10n (Weblate-ready)

## Setup first
- ```python -m venv venv```
- ```venv\Scripts\activate.bat```
- ```pip install pandas openpyxl python-docx pymupdf```

## Generate basic repository

```
mkdir scripts
curl -L https://raw.githubusercontent.com/PiAir/digcomp3-l10n/refs/heads/main/scripts/build_digcomp_weblate_repo_steps_v3.py -o  scripts\build_digcomp_weblate_repo_steps.py
mkdir sources
curl -L https://github.com/PiAir/digcomp3-l10n/raw/refs/heads/main/sources/DigComp%203.0%20Data%20Supplement%2024%20Nov%202025.xlsx -o "sources\DigComp 3.0 Data Supplement 24 Nov 2025.xlsx"

python scripts\build_digcomp_weblate_repo_steps.py step1 --xlsx "sources\DigComp 3.0 Data Supplement 24 Nov 2025.xlsx"
```
## Repository generated

CSV format: location,source,target (UTF-8)

Components:
- core-framework
- levels
- statements
- outcomes
- glossary
- acronyms

A texts folder is created, but this can be ignored.


or:

## Export the repository from github

```
git clone https://github.com/PiAir/digcomp3-l10n.git
```
## Repository downloaded:
- images
- locale
- output
- scripts
- sources


# TODO: update process (20260112)

## Terminologie (EN -> NL)
- “Competence area” → “Competentiegebied”
- “Competence” → “Competentie”
- “Proficiency levels” → “Beheersingsniveaus”
- “Learning outcomes” → “Leerresultaten”
