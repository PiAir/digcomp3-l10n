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
    - acronyms
    - core-frameowk
    - glossary
    - levels
    - odt
    - outcompes
    - statements
- output
- scripts
- sources


## Terminologie (EN -> NL)
- “Competence area” → “Competentiegebied”
- “Competence” → “Competentie”
- “Proficiency levels” → “Beheersingsniveaus”
- “Learning outcomes” → “Leerresultaten”

## Disclaimer / Disclosure
This repository contains scripts and files related to the creation of the Dutch translation of the DigComp 3.0 European Digital Competence Framework, Fith Edition.

Original source: Cosgrove, J. and Cachia, R., DigComp 3.0: European Digital Competence Framework - Fifth Edition, Publications Office of the European Union, Luxembourg, 2025, [https://data.europa.eu/doi/10.2760/0001149](https://data.europa.eu/doi/10.2760/0001149), JRC144121.

The European Commission is not responsible for the modified, adapted or translated versions available through this repository.
The European Commission allows the translation of DigComp 3.0 into other languages, but not endorse the modified, adapted or translated version.
The reuse policy of the European Commission documents is implemented by the Commission Decision 2011/833/EU of 12 December 2011 on the reuse of Commission documents (OJ L 330, 14.12.2011, p. 39). Unless otherwise noted, the reuse of the original DigComp document is authorised under the Creative Commons Attribution 4.0 International (CC BY 4.0) licence (https://creativecommons.org/licenses/by/4.0/). 

The translation into Dutch is done under the auspices of the [iXperium Centre of Expertise Teaching and Learning](https://ixperium.nl/)

No changes have been made to the original competence areas, competences, proficiency levels, learning outcomes that are part of DigComp other than a translation from English to Dutch while keeping the intention and meaning of the wording as close as possible to the original.
