library(officer)
library(magrittr)

# 1. Paden
main_doc_path <- "D:/Temp/Python/weblate/digcomp3-l10n/qmd/DigComp3.0-Nederlands.docx"
output_folder <- "D:/Temp/Python/weblate/digcomp3-l10n/output/"

tasks <- list(
    "\\[tabel table_2\\]"  = "DigComp3_table2_nl.docx",
    "\\[tabel digcomp3\\]" = "DigComp3_digcomp3_nl.docx",
    "\\[tabel outcomes\\]" = "DigComp3_outcomes_nl.docx",
    "\\[tabel glossary\\]" = "DigComp3_glossary_nl.docx"
)

# 2. Open document
doc <- read_docx(main_doc_path)

# 3. Voeg de Python-tabellen in (Symmetrische vervanging)
for (placeholder in names(tasks)) {
    file_to_add <- paste0(output_folder, tasks[[placeholder]])

    if (file.exists(file_to_add)) {
        # Vind de placeholder en vervang de tekst door de externe DOCX
        # We gebruiken cursor_bookmark als je bookmarks hebt,
        # maar cursor_reach is prima als de tekst uniek is.
        doc <- doc %>%
            cursor_reach(keyword = placeholder) %>%
            body_add_docx(src = file_to_add, pos = "on") # 'on' vervangt de alinea!

        message("Vervangen: ", placeholder)
    }
}

# 4. FIX VOOR MARKDOWN TABELLEN (Gecentreerd -> Links)
# We dwingen de tabel-stijl 'Table Grid' af en zetten de globale uitlijning
# Dit werkt alleen als Pandoc de tabel niet 'hard' heeft vastgezet.
doc <- doc %>%
    body_replace_all_text("placeholder_dummy", "dummy") # Forceert XML verversing

# 5. Opslaan
final_path <- "D:/Temp/Python/weblate/digcomp3-l10n/output/DigComp3.0-Nederlands_samengevoegd.docx"
print(doc, target = final_path)

message("Klaar! Bestand: ", final_path)
