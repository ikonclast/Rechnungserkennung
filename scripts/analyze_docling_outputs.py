#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


INVOICE_NUMBER_PATTERNS = [
    re.compile(r"\bDRP\d{6,}\b"),
    re.compile(r"\bINV-\d[\w-]*\b"),
    re.compile(r"\bDS-AEU-INV-DE-\d{4}-\d+\b"),
    re.compile(r"\bAUDDE-INV-DE-\d{4}-\d+\b"),
    re.compile(r"\b[A-Z]{2,}\d{4,}[A-Z0-9-]*\b"),
]

DATE_PATTERNS = [
    re.compile(r"Rechnungsdatum", re.IGNORECASE),
    re.compile(r"\bDate:\b"),
    re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b"),
    re.compile(r"\b\d{2} [A-Za-z]+ \d{4}\b"),
]

AMOUNT_PATTERNS = [
    re.compile(r"Zahlbetrag", re.IGNORECASE),
    re.compile(r"Gesamtbetrag", re.IGNORECASE),
    re.compile(r"Zu zahlender Betrag", re.IGNORECASE),
    re.compile(r"Rechnungsbetrag", re.IGNORECASE),
    re.compile(r"faellig", re.IGNORECASE),
]

VAT_PATTERNS = [
    re.compile(r"USt", re.IGNORECASE),
    re.compile(r"Umsatzsteuer", re.IGNORECASE),
    re.compile(r"MwSt", re.IGNORECASE),
    re.compile(r"VAT", re.IGNORECASE),
]

IBAN_PATTERN = re.compile(r"\bIBAN\b", re.IGNORECASE)
IMAGE_PATTERN = re.compile(r"!\[Image\]\(data:image/", re.IGNORECASE)
TABLE_ROW_PATTERN = re.compile(r"^\|.*\|$", re.MULTILINE)
SEPARATOR_PATTERN = re.compile(r"={8,}")
BROKEN_DATE_LABEL_PATTERN = re.compile(r"^/Lieferdatum$", re.MULTILINE)


def detect_supplier(text: str) -> str:
    supplier_markers = [
        ("STRATO", "strato"),
        ("congstar", "congstar"),
        ("Amazon", "amazon"),
        ("INTERSPORT", "intersport"),
        ("Audible", "audible"),
        ("Fenerofolio", "fenerofolio"),
        ("Stripe", "stripe"),
    ]
    for needle, label in supplier_markers:
        if needle.lower() in text.lower():
            return label
    return "unbekannt"


def repeated_heading_count(text: str) -> int:
    headings = re.findall(r"^##\s+(.+)$", text, flags=re.MULTILINE)
    if not headings:
        return 0
    counts = Counter(headings)
    return sum(1 for value in counts.values() if value > 1)


def repeated_table_lines(text: str) -> int:
    rows = TABLE_ROW_PATTERN.findall(text)
    suspicious = 0
    for row in rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        cells = [cell for cell in cells if cell]
        if not cells:
            continue
        unique = set(cells)
        if len(cells) >= 4 and len(unique) <= max(1, len(cells) // 2):
            suspicious += 1
    return suspicious


def has_pattern(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def collect_invoice_numbers(text: str) -> list[str]:
    matches: list[str] = []
    for pattern in INVOICE_NUMBER_PATTERNS:
        matches.extend(pattern.findall(text))
    deduped = []
    seen = set()
    for match in matches:
        if match not in seen:
            seen.add(match)
            deduped.append(match)
    return deduped


def analyze_file(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    invoice_numbers = collect_invoice_numbers(text)
    table_count = len(TABLE_ROW_PATTERN.findall(text))
    issues: list[str] = []

    if IMAGE_PATTERN.search(text):
        issues.append("eingebettetes_base64_bild")
    if repeated_heading_count(text) > 0:
        issues.append("doppelte_heading")
    if repeated_table_lines(text) > 0:
        issues.append("wiederholte_tabellenzellen")
    if SEPARATOR_PATTERN.search(text):
        issues.append("separator_aus_pdf_uebernommen")
    if BROKEN_DATE_LABEL_PATTERN.search(text):
        issues.append("datumslabel_gebrochen")
    if not invoice_numbers:
        issues.append("rechnungsnummer_nicht_eindeutig_erkannt")
    if not has_pattern(text, DATE_PATTERNS):
        issues.append("datum_nicht_eindeutig_erkannt")
    if not has_pattern(text, AMOUNT_PATTERNS):
        issues.append("betrag_nicht_eindeutig_erkannt")

    return {
        "file": path.name,
        "supplier": detect_supplier(text),
        "invoice_numbers": invoice_numbers,
        "has_amount": has_pattern(text, AMOUNT_PATTERNS),
        "has_date": has_pattern(text, DATE_PATTERNS),
        "has_vat": has_pattern(text, VAT_PATTERNS),
        "has_iban": bool(IBAN_PATTERN.search(text)),
        "table_rows": table_count,
        "issues": issues,
    }


def render_report(results: list[dict[str, object]]) -> str:
    issue_counter: Counter[str] = Counter()
    supplier_counter: Counter[str] = Counter()
    for result in results:
        supplier_counter[result["supplier"]] += 1
        issue_counter.update(result["issues"])

    lines: list[str] = []
    lines.append("# Docling Analyse")
    lines.append("")
    lines.append(f"Dateien: {len(results)}")
    lines.append("")
    lines.append("## Nach Lieferantentyp")
    lines.append("")
    for supplier, count in sorted(supplier_counter.items()):
        lines.append(f"- {supplier}: {count}")
    lines.append("")
    lines.append("## Haeufige Auffaelligkeiten")
    lines.append("")
    for issue, count in issue_counter.most_common():
        lines.append(f"- {issue}: {count}")
    lines.append("")
    lines.append("## Pro Datei")
    lines.append("")
    for result in results:
        issues = ", ".join(result["issues"]) if result["issues"] else "keine_heuristische_auffaelligkeit"
        invoice_numbers = ", ".join(result["invoice_numbers"]) if result["invoice_numbers"] else "-"
        lines.append(
            f"- {result['file']}: supplier={result['supplier']}, "
            f"rechnungsnummer={invoice_numbers}, "
            f"datum={result['has_date']}, betrag={result['has_amount']}, "
            f"ust={result['has_vat']}, iban={result['has_iban']}, "
            f"tabellenzeilen={result['table_rows']}, issues={issues}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analysiert Docling-Markdown-Dateien heuristisch.")
    parser.add_argument("directory", type=Path, help="Ordner mit .md-Ausgaben")
    args = parser.parse_args()

    files = sorted(args.directory.glob("*.md"))
    if not files:
        raise SystemExit(f"Keine Markdown-Dateien in {args.directory}")

    results = [analyze_file(path) for path in files]
    print(render_report(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
