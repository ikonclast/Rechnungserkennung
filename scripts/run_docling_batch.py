#!/home/tobias/rechnungserkennung/.venv/bin/python
"""run_docling_batch.py

Führt alle PDFs aus einem Ordner durch Docling aus.
Speichert Outputs als Markdown in output/docling/realtestdata_final/

Nutzung:
    python3 scripts/run_docling_batch.py samples/realtestdata/ output/docling/realtestdata_final/
"""

import sys
import json
from pathlib import Path
from docling.document_converter import DocumentConverter
from docling_core.types.doc import DocItemLabel
from docling_core.types.doc.document import ContentLayer

# Labels und Content-Layer für den Markdown-Export.
# FURNITURE eingeschlossen damit PAGE_FOOTER (IBAN, BIC, Steuernummern) mitkommt.
MARKDOWN_LABELS = {
    DocItemLabel.TEXT,
    DocItemLabel.PARAGRAPH,
    DocItemLabel.TITLE,
    DocItemLabel.SECTION_HEADER,
    DocItemLabel.TABLE,
    DocItemLabel.LIST_ITEM,
    DocItemLabel.CAPTION,
    DocItemLabel.FOOTNOTE,
    DocItemLabel.PAGE_FOOTER,
}
MARKDOWN_LAYERS = {ContentLayer.BODY, ContentLayer.FURNITURE}

def run_docling_batch(input_dir: str, output_dir: str):
    """Führt alle PDFs durch Docling durch."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Finde alle PDFs
    pdf_files = sorted(input_path.glob("*.pdf"))
    print(f"Gefunden: {len(pdf_files)} PDF-Dateien")
    print(f"Output-Verzeichnis: {output_path}\n")

    converter = DocumentConverter()

    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")

        try:
            # Docling konvertiert PDF zu DocumentElement
            doc_result = converter.convert(str(pdf_file))

            # Markdownexport — FURNITURE-Layer eingeschlossen für IBAN/BIC im Footer
            md_output = output_path / f"{pdf_file.stem}.md"
            md_text = doc_result.document.export_to_markdown(
                labels=MARKDOWN_LABELS,
                included_content_layers=MARKDOWN_LAYERS,
            )
            md_output.write_text(md_text, encoding="utf-8")

            # JSON für Debugging (optional)
            json_output = output_path / f"{pdf_file.stem}.json"
            doc_result.document.save_as_json(str(json_output))

            print(f"  ✓ → {md_output.name}")

        except Exception as e:
            print(f"  ✗ Fehler: {e}")
            continue

    print(f"\n✅ Fertig! {len(list(output_path.glob('*.md')))} Markdown-Dateien erstellt.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Nutzung: python3 scripts/run_docling_batch.py <input_dir> <output_dir>")
        print("Beispiel: python3 scripts/run_docling_batch.py samples/realtestdata/ output/docling/realtestdata_final/")
        sys.exit(1)

    run_docling_batch(sys.argv[1], sys.argv[2])
