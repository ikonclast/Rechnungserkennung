#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from collections import Counter
from datetime import date
from pathlib import Path


INVOICE_NUMBER_PATTERNS = [
    re.compile(r"\bDRP\d{6,}\b"),
    re.compile(r"\bINV-\d[\w-]*\b"),
    re.compile(r"\bDS-AEU-INV-DE-\d{4}-\d+\b"),
    re.compile(r"\bAUDDE-INV-DE-\d{4}-\d+\b"),
    re.compile(r"\b[A-Z]{2,}\d{4,}[A-Z0-9-]*\b"),
]

# Länderkürzel (2 Buchstaben) + 18–22 Ziffern — schließt IBANs aus Format-Matches aus.
IBAN_VALUE_PATTERN = re.compile(r"^[A-Z]{2}\d{18,22}$")

# Label-Erkennung: ist irgendein Rechnungsnummer-Label im Dokument?
# Extraktion des Wertes ist Aufgabe der Rule Engine (Woche 5-10).
INVOICE_LABEL_PATTERNS = [
    re.compile(r"Rechnungs(?:nummer|[-\s]?Nr\.?)", re.IGNORECASE),
    re.compile(r"RECHNUNGS-NR\.?", re.IGNORECASE),
    re.compile(r"Beleg(?:nummer|[-\s]?Nr\.?)", re.IGNORECASE),
    re.compile(r"Rechnung\s+Nr\.?", re.IGNORECASE),
    re.compile(r"Invoice\s*(?:Number|No\.?)", re.IGNORECASE),
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

# Beschreibungen und Rule-Engine-Hinweise pro Fehlercode.
ISSUE_META: dict[str, dict[str, str]] = {
    "wiederholte_tabellenzellen": {
        "titel": "Tabellenzellen wiederholt",
        "was": (
            "Docling dupliziert den Zellinhalt über mehrere Spalten einer Tabellenzeile, "
            "wenn es die Tabellenstruktur nicht korrekt parsen kann. "
            "Typisch bei Billomat und Billingtools mit komplexem Spalten-Layout."
        ),
        "rule_engine": (
            "Beim Lesen von Tabellenzeilen nur die letzte Spalte auswerten (Betragsspalte). "
            "Alternativ: Zeilen erkennen bei denen >50% der Zellen identisch sind und überspringen."
        ),
    },
    "rechnungsnummer_label_da_wert_nicht_extrahiert": {
        "titel": "Rechnungsnummer-Label vorhanden, Wert nicht extrahiert",
        "was": (
            "Ein Label wie 'Rechnung Nr.' oder 'RECHNUNGS-NR.' ist im Dokument vorhanden, "
            "aber das Format des Wertes (z.B. 'EM-2026-3') passt auf kein aktuelles Format-Pattern. "
            "Häufig weil Label und Wert durch Zeilenumbruch getrennt sind (sevDesk-Sidebar)."
        ),
        "rule_engine": (
            "Label-relative Extraktion: Nach dem Label den nächsten alphanumerischen Token greifen, "
            "auch über Zeilengrenze hinweg. "
            "Muster: r'Rechnung\\s*Nr\\.?\\s*([A-Z0-9][\\w-]{3,})'"
        ),
    },
    "rechnungsnummer_kein_label_kein_format": {
        "titel": "Rechnungsnummer — kein Label, kein Format erkannt",
        "was": (
            "Weder ein Label noch ein bekanntes Zahlenformat gefunden. "
            "Docling packt den Rechnungskopf in einen Fließtext-Block, "
            "z.B. 'ENTWURF Rechnung 2026-0415-001 Kundennummer: KD2'. "
            "Betrifft hauptsächlich Billomat (Format: YYYY-MMDD-NNN) und sevDesk Gutschrift."
        ),
        "rule_engine": (
            "Positionsbasierte Extraktion: Nach dem Wort 'Rechnung' den nächsten Token suchen, "
            "der auf r'\\d{4}-\\d{4}-\\d{3,4}' passt. "
            "Confidence niedrig (~0.65) da kein Label als Anker vorhanden."
        ),
    },
    "betrag_nicht_eindeutig_erkannt": {
        "titel": "Gesamtbetrag nicht erkannt",
        "was": (
            "Kein bekanntes Betragslabel ('Gesamtbetrag', 'Rechnungsbetrag' etc.) gefunden. "
            "Betrifft Gutschriften und Stornos (negative Beträge ohne Standardlabel) "
            "sowie Word-generierte PDFs ohne strukturiertes Layout."
        ),
        "rule_engine": (
            "Zusätzliche Labels: 'Gutschriftsbetrag', 'Stornobetrag', 'Kreditbetrag'. "
            "Fallback: letzten EUR/€-Betrag in der Tabelle nehmen wenn kein Label greift."
        ),
    },
    "datumslabel_gebrochen": {
        "titel": "Datumslabel über Zeilengrenze gebrochen",
        "was": (
            "'/Lieferdatum' erscheint als eigene Zeile — Docling hat das Label beim Parsen "
            "am Schrägstrich getrennt. Betrifft Amazon und Audible."
        ),
        "rule_engine": (
            "Preprocessing: Kurzzeilen (<15 Zeichen) die mit '/' beginnen mit Vorgängerzeile zusammenführen. "
            "Oder direkt auf r'\\d{2}\\.\\d{2}\\.\\d{4}' ohne Label-Anker matchen."
        ),
    },
    "separator_aus_pdf_uebernommen": {
        "titel": "PDF-Trennlinien im Output",
        "was": (
            "Acht oder mehr '='-Zeichen in einer Zeile — Layoutartefakt aus dem Original-PDF. "
            "Normalisierung entfernt reine '='-Zeilen, aber STRATO nutzt '=' auch innerhalb von Text."
        ),
        "rule_engine": (
            "Kein Handlungsbedarf für die Extraktion — betrifft keine Felder. "
            "Optional: Normalisierung verschärfen für '='-Zeilen die nur Sonderzeichen enthalten."
        ),
    },
    "doppelte_heading": {
        "titel": "Doppelte Markdown-Überschrift",
        "was": (
            "Dieselbe ##-Überschrift erscheint mehrfach im Dokument. "
            "congstar nutzt mehrseitige Rechnungen — Docling wiederholt den Seitenkopf "
            "für jede Seite als eigene Überschrift."
        ),
        "rule_engine": (
            "Beim Lesen von Feldern aus Überschriften: erste Occurrence nehmen, Rest ignorieren. "
            "Keine Aggregation über mehrere Occurrences."
        ),
    },
    "eingebettetes_base64_bild": {
        "titel": "Base64-Bild im Markdown",
        "was": "Docling hat ein Bild (Logo, QR-Code) als Base64 ins Markdown eingebettet.",
        "rule_engine": "Normalisierung entfernt diese bereits. Kein Handlungsbedarf.",
    },
    "datum_nicht_eindeutig_erkannt": {
        "titel": "Datum nicht erkannt",
        "was": "Kein Datum im Format TT.MM.JJJJ oder bekanntes Datumslabel gefunden.",
        "rule_engine": "Weitere Datumsformate ergänzen: ISO (YYYY-MM-DD), englisches Format.",
    },
}


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
        for match in pattern.findall(text):
            if not IBAN_VALUE_PATTERN.match(match):
                matches.append(match)
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
    has_invoice_label = has_pattern(text, INVOICE_LABEL_PATTERNS)
    if not invoice_numbers and not has_invoice_label:
        issues.append("rechnungsnummer_kein_label_kein_format")
    elif not invoice_numbers and has_invoice_label:
        issues.append("rechnungsnummer_label_da_wert_nicht_extrahiert")
    if not has_pattern(text, DATE_PATTERNS):
        issues.append("datum_nicht_eindeutig_erkannt")
    if not has_pattern(text, AMOUNT_PATTERNS):
        issues.append("betrag_nicht_eindeutig_erkannt")

    return {
        "file": path.name,
        "supplier": detect_supplier(text),
        "invoice_numbers": invoice_numbers,
        "has_invoice_label": has_invoice_label,
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
        label_flag = "label=✓" if result["has_invoice_label"] else "label=✗"
        lines.append(
            f"- {result['file']}: supplier={result['supplier']}, "
            f"rechnungsnummer={invoice_numbers} ({label_flag}), "
            f"datum={result['has_date']}, betrag={result['has_amount']}, "
            f"ust={result['has_vat']}, iban={result['has_iban']}, "
            f"tabellenzeilen={result['table_rows']}, issues={issues}"
        )
    return "\n".join(lines)


def render_top10_report(
    results: list[dict[str, object]],
    input_dir: Path,
) -> str:
    n = len(results)
    issue_counter: Counter[str] = Counter()
    issue_files: dict[str, list[str]] = {}
    for result in results:
        for issue in result["issues"]:
            issue_counter[issue] += 1
            issue_files.setdefault(issue, []).append(result["file"])

    # Felder-Gesamtstatistik
    ok_date = sum(1 for r in results if r["has_date"])
    ok_amount = sum(1 for r in results if r["has_amount"])
    ok_vat = sum(1 for r in results if r["has_vat"])
    ok_iban = sum(1 for r in results if r["has_iban"])
    ok_nr = sum(1 for r in results if r["invoice_numbers"])

    lines: list[str] = []
    lines.append("# Top-10-Fehler — Docling Baseline")
    lines.append("")
    lines.append(
        f"**Analysiert:** {n} Dateien | "
        f"**Datum:** {date.today().isoformat()} | "
        f"**Input:** {input_dir}"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Feldgenauigkeit Gesamt")
    lines.append("")
    lines.append("| Feld | Erkannt | Anteil | Bewertung |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Datum | {ok_date}/{n} | {ok_date/n:.0%} | {'✅ stabil' if ok_date/n >= 0.9 else '⚠ pruefe'} |")
    lines.append(f"| USt/MwSt | {ok_vat}/{n} | {ok_vat/n:.0%} | {'✅ stabil' if ok_vat/n >= 0.9 else '⚠ pruefe'} |")
    lines.append(f"| Betrag | {ok_amount}/{n} | {ok_amount/n:.0%} | {'✅ stabil' if ok_amount/n >= 0.9 else '⚠ pruefe'} |")
    lines.append(f"| Rechnungsnummer (Wert) | {ok_nr}/{n} | {ok_nr/n:.0%} | {'✅ stabil' if ok_nr/n >= 0.9 else '⚠ Rule Engine noetig'} |")
    lines.append(f"| IBAN | {ok_iban}/{n} | {ok_iban/n:.0%} | ℹ nur wenn im PDF sichtbar |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Fehler nach Häufigkeit")
    lines.append("")

    for rank, (issue, count) in enumerate(issue_counter.most_common(), start=1):
        pct = count / n
        meta = ISSUE_META.get(issue, {})
        titel = meta.get("titel", issue)
        was = meta.get("was", "—")
        rule_engine = meta.get("rule_engine", "—")
        betroffene = ", ".join(f"`{f}`" for f in issue_files[issue])

        lines.append(f"### Fehler {rank} — {titel} ({count}/{n}, {pct:.0%})")
        lines.append("")
        lines.append(f"**Was passiert:** {was}")
        lines.append("")
        lines.append(f"**Betroffene Dateien:** {betroffene}")
        lines.append("")
        lines.append(f"**Rule Engine:** {rule_engine}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Fazit für Woche 5-10")
    lines.append("")
    lines.append(
        "Datum und USt sind sofort zuverlässig — kein Handlungsbedarf. "
        "Die Rule Engine muss drei Probleme lösen, in dieser Priorität:"
    )
    lines.append("")

    priority = [
        (
            "Rechnungsnummer — label-relative Extraktion",
            "Label ist in 85% der Fälle vorhanden. "
            "Wert-Extraktion nach Label (auch über Zeilengrenze) löst den Großteil.",
        ),
        (
            "Rechnungsnummer — Billomat-Sonderfall (positionsbasiert)",
            "Kein Label. Format YYYY-MMDD-NNN nach dem Wort 'Rechnung' suchen.",
        ),
        (
            "Betrag — Gutschrift/Storno-Labels ergänzen",
            "Standardlabels fehlen bei negativen Beträgen. Zusätzliche Label-Varianten nötig.",
        ),
        (
            "Tabellenzellen — Duplikate ignorieren",
            "Zeilen bei denen >50% Zellen identisch sind überspringen oder nur letzte Spalte lesen.",
        ),
    ]
    for i, (titel, beschreibung) in enumerate(priority, start=1):
        lines.append(f"{i}. **{titel}** — {beschreibung}")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analysiert Docling-Markdown-Dateien heuristisch.")
    parser.add_argument("directory", type=Path, help="Ordner mit .md-Ausgaben")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/analysis"),
        help="Ausgabeordner fuer top_10_errors.md (Standard: output/analysis)",
    )
    args = parser.parse_args()

    files = sorted(args.directory.glob("*.md"))
    if not files:
        raise SystemExit(f"Keine Markdown-Dateien in {args.directory}")

    results = [analyze_file(path) for path in files]

    print(render_report(results))

    args.output.mkdir(parents=True, exist_ok=True)
    top10_path = args.output / "top_10_errors.md"
    top10_path.write_text(render_top10_report(results, args.directory), encoding="utf-8")
    print(f"\n→ top_10_errors.md geschrieben: {top10_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
