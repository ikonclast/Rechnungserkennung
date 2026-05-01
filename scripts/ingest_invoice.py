#!/usr/bin/env python3
"""ingest_invoice.py

Vollständige Ingestion-Pipeline für eine einzelne Rechnung oder einen Ordner:
  PDF → SHA-256 → Duplikat-Check → MinIO → documents INSERT
      → Docling → normalize → Rule Engine → extractions INSERT

Nutzung:
    # Eine Rechnung:
    .venv/bin/python scripts/ingest_invoice.py samples/realtestdata/fastbill_standard_001.pdf

    # Ganzer Ordner:
    .venv/bin/python scripts/ingest_invoice.py samples/realtestdata/
"""

import hashlib
import sys
from datetime import date, timedelta
from pathlib import Path

# Projektpfad in sys.path damit src.* importierbar ist
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# .env laden (Credentials für DB + MinIO)
def _load_env():
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    import os
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() not in os.environ:
            os.environ[key.strip()] = value.strip()

_load_env()

from src.db import get_conn
from src import storage
from src.extraction.rule_engine import extract_from_file
from src.validation import check_all

# Docling-Imports — selbe Konfiguration wie run_docling_batch.py
from docling.document_converter import DocumentConverter
from docling_core.types.doc import DocItemLabel
from docling_core.types.doc.document import ContentLayer

# Normalize-Funktion direkt aus dem bestehenden Script importieren
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from normalize_docling_output import normalize_file

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

# Ausgabeverzeichnisse für Zwischen-Artefakte (für Debugging aufbewahren)
DOCLING_OUT  = PROJECT_ROOT / "output" / "docling"  / "ingested"
NORM_OUT     = PROJECT_ROOT / "output" / "normalized" / "ingested"


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_docling(pdf_path: Path) -> Path:
    """Konvertiert PDF zu Markdown via Docling. Gibt Pfad zur .md zurück."""
    DOCLING_OUT.mkdir(parents=True, exist_ok=True)
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    md_text = result.document.export_to_markdown(
        labels=MARKDOWN_LABELS,
        included_content_layers=MARKDOWN_LAYERS,
    )
    md_path = DOCLING_OUT / f"{pdf_path.stem}.md"
    md_path.write_text(md_text, encoding="utf-8")
    return md_path


def run_normalize(raw_md: Path) -> Path:
    """Bereinigt Docling-Markdown. Gibt Pfad zur normalisierten .md zurück."""
    NORM_OUT.mkdir(parents=True, exist_ok=True)
    norm_path = NORM_OUT / raw_md.name
    normalize_file(raw_md, norm_path)
    return norm_path


# ---------------------------------------------------------------------------
# Kern-Logik
# ---------------------------------------------------------------------------

def ingest(pdf_path: Path) -> bool:
    """
    Ingestiert eine einzelne Rechnung.
    Gibt True zurück wenn neu angelegt, False wenn Duplikat.
    """
    print(f"\n{'─'*55}")
    print(f"  {pdf_path.name}")
    print(f"{'─'*55}")

    # 1. SHA-256
    sha = sha256_of_file(pdf_path)
    print(f"  SHA-256  {sha[:16]}…")

    with get_conn() as conn:
        cur = conn.cursor()

        # 2. Duplikat-Check
        cur.execute("SELECT id, filename FROM documents WHERE sha256 = %s", (sha,))
        existing = cur.fetchone()
        if existing:
            print(f"  DUPLIKAT — identisch mit Dokument #{existing[0]} ({existing[1]})")
            return False

        # 3. MinIO Upload
        object_name = f"{sha[:8]}/{pdf_path.name}"
        minio_path = storage.upload(str(pdf_path), object_name)
        print(f"  MinIO    {minio_path}")

        # 4. documents INSERT
        retain_until = date.today() + timedelta(days=3_650)  # 10 Jahre GoBD
        cur.execute(
            """
            INSERT INTO documents (sha256, filename, minio_path, retain_until)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (sha, pdf_path.name, minio_path, retain_until),
        )
        doc_id = cur.fetchone()[0]
        print(f"  DB       documents #{doc_id}  (aufbewahren bis {retain_until})")

        # 5. Docling
        print(f"  Docling  läuft…", end="", flush=True)
        raw_md = run_docling(pdf_path)
        print(f" → {raw_md.name}")

        # 6. Normalisierung
        norm_md = run_normalize(raw_md)

        # 7. Rule Engine
        result = extract_from_file(norm_md)

        # 8. extractions INSERT
        cur.execute(
            """
            INSERT INTO extractions (
                document_id, engine_version,
                rechnungsnummer, rechnungsnummer_conf,
                datum,          datum_conf,
                betrag_brutto,  betrag_brutto_conf,
                mwst_betrag,    mwst_betrag_conf,
                netto_betrag,   netto_betrag_conf,
                mwst_satz,      mwst_satz_conf,
                dokumenttyp,    dokumenttyp_conf,
                lieferant_name, lieferant_name_conf,
                steuernummer,   steuernummer_conf,
                iban,           iban_conf
            ) VALUES (
                %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                doc_id, "rule_engine_v1",
                result["rechnungsnummer"]["value"], result["rechnungsnummer"]["confidence"],
                result["datum"]["value"],           result["datum"]["confidence"],
                result["betrag_brutto"]["value"],   result["betrag_brutto"]["confidence"],
                result["mwst_betrag"]["value"],     result["mwst_betrag"]["confidence"],
                result["netto_betrag"]["value"],    result["netto_betrag"]["confidence"],
                result["mwst_satz"]["value"],       result["mwst_satz"]["confidence"],
                result["dokumenttyp"]["value"],     result["dokumenttyp"]["confidence"],
                result["lieferant_name"]["value"],  result["lieferant_name"]["confidence"],
                result["steuernummer"]["value"],    result["steuernummer"]["confidence"],
                result["iban"]["value"],            result["iban"]["confidence"],
            ),
        )
        extr_id = cur.fetchone()[0]

        # 9. Validierung + validations INSERT
        checks = check_all(result)
        for c in checks:
            cur.execute(
                """
                INSERT INTO validations (extraction_id, check_name, result, detail)
                VALUES (%s, %s, %s, %s)
                """,
                (extr_id, c["check_name"], c["result"], c["detail"]),
            )

    # Ergebnis ausgeben
    r = result
    def fmt(field):
        v = r[field]["value"]
        c = r[field]["confidence"]
        return f"{v}  ({c:.0%})" if v else "—"

    print(f"  Extraktion #{extr_id}:")
    print(f"    Rechnungsnr.  {fmt('rechnungsnummer')}")
    print(f"    Datum         {fmt('datum')}")
    print(f"    Brutto        {fmt('betrag_brutto')} €")
    print(f"    MwSt          {fmt('mwst_betrag')} €  [{fmt('mwst_satz')}%]")
    print(f"    Netto         {fmt('netto_betrag')} €")
    print(f"    Typ           {fmt('dokumenttyp')}")
    print(f"    Lieferant     {fmt('lieferant_name')}")

    # Validierungs-Zusammenfassung
    fails = [c for c in checks if c["result"] == "fail"]
    warns = [c for c in checks if c["result"] == "warn"]
    if fails or warns:
        print(f"  Validierung: {len(fails)} FAIL  {len(warns)} WARN")
        for c in fails + warns:
            marker = "✗ FAIL" if c["result"] == "fail" else "⚠ WARN"
            print(f"    {marker}  {c['detail']}")
    else:
        print(f"  Validierung: alle Checks OK")

    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Nutzung:")
        print("  .venv/bin/python scripts/ingest_invoice.py <datei.pdf>")
        print("  .venv/bin/python scripts/ingest_invoice.py <ordner/>")
        sys.exit(1)

    target = Path(sys.argv[1])

    if target.is_dir():
        pdfs = sorted(target.glob("*.pdf"))
        if not pdfs:
            print(f"Keine PDFs in {target}")
            sys.exit(1)
        print(f"Ingestiere {len(pdfs)} PDFs aus {target}")
        neu = dupl = 0
        for pdf in pdfs:
            if ingest(pdf):
                neu += 1
            else:
                dupl += 1
        print(f"\n{'═'*55}")
        print(f"  Fertig: {neu} neu angelegt, {dupl} Duplikate übersprungen")
    elif target.is_file() and target.suffix.lower() == ".pdf":
        ingest(target)
    else:
        print(f"Fehler: {target} ist keine PDF-Datei und kein Ordner")
        sys.exit(1)


if __name__ == "__main__":
    main()
