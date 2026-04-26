#!/usr/bin/env python3
"""normalize_docling_output.py

Bereinigt Docling-Markdown-Ausgaben fuer spaetere Feldextraktion.

Zwei Schritte — beide rein subtraktiv, kein semantischer Eingriff:
  1. Base64-Bilder entfernen  (Logos, QR-Codes — kein Feldinhalt)
  2. Standalone-Separator-Zeilen entfernen  (===== — reines PDF-Layout-Artefakt)

Bewusst NICHT in diesem Schritt:
  - Tabellen anfassen  (Struktur zu fragil, Semantik kann verloren gehen)
  - Datumslabels normalisieren  (zu lieferantenspezifisch fuer einen generischen Fix)
  Beides ist Aufgabe der Rule Engine (Wochen 5-10).

Nach jeder Datei: Felderhaltungscheck — warnt wenn fachwichtige Signale
(Betrag, Datum, IBAN, Rechnungsnummer, Steuer) im Output verschwunden sind.

Nutzung:
    python3 scripts/normalize_docling_output.py <input_dir> <output_dir>

Beispiel:
    python3 scripts/normalize_docling_output.py \\
        output/docling/realtestdata \\
        output/normalized/realtestdata
"""

import re
import sys
from pathlib import Path

# Heuristiken fuer den Felderhaltungscheck.
# Jeder Eintrag: (Label, Regex).
# Wenn ein Signal im Original vorhanden, muss es auch im Output vorhanden sein.
FIELD_SIGNALS = [
    ('Betrag',          re.compile(r'(?:€|EUR)')),
    ('Datum',           re.compile(r'\d{1,2}[./]\d{1,2}[./]\d{4}')),
    ('IBAN',            re.compile(r'IBAN')),
    ('Rechnungsnummer', re.compile(r'(?:Rechnungsnummer|Rechnungs-Nr|Invoice)')),
    ('Steuer',          re.compile(r'(?:USt|MwSt|Steuer)')),
]


def remove_base64_images(text: str) -> str:
    return re.sub(r'!\[[^\]]*\]\(data:image/[^)]+\)\n?', '', text)


def remove_separators(text: str) -> str:
    # Nur Zeilen die ausschliesslich aus = bestehen (mind. 3).
    # Zeilen wie "Brutto =======" (Text + =) bleiben unveraendert.
    lines = text.splitlines(keepends=True)
    return ''.join(
        line for line in lines
        if not re.match(r'^={3,}\s*$', line.strip())
    )


def check_field_retention(original: str, normalized: str, filename: str) -> list[str]:
    warnings = []
    for label, pattern in FIELD_SIGNALS:
        if pattern.search(original) and not pattern.search(normalized):
            warnings.append(f'    ⚠  {label}-Signal verschwunden ({pattern.pattern})')
    return warnings


def normalize_file(input_path: Path, output_path: Path) -> dict:
    original = input_path.read_text(encoding='utf-8')

    normalized = remove_base64_images(original)
    normalized = remove_separators(normalized)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(normalized, encoding='utf-8')

    warnings = check_field_retention(original, normalized, input_path.name)
    reduction = round((1 - len(normalized) / len(original)) * 100, 1) if original else 0

    return {
        'file': input_path.name,
        'original_bytes': len(original),
        'normalized_bytes': len(normalized),
        'reduction_pct': reduction,
        'warnings': warnings,
    }


def main():
    if len(sys.argv) != 3:
        print(f'Nutzung: {sys.argv[0]} <input_dir> <output_dir>')
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if not input_dir.is_dir():
        print(f'Fehler: {input_dir} ist kein Verzeichnis')
        sys.exit(1)

    md_files = sorted(input_dir.glob('*.md'))
    if not md_files:
        print(f'Keine .md-Dateien in {input_dir} gefunden')
        sys.exit(1)

    print(f'Normalisiere {len(md_files)} Dateien: {input_dir} → {output_dir}\n')

    total_original = 0
    total_normalized = 0
    total_warnings = 0

    for input_path in md_files:
        output_path = output_dir / input_path.name
        stats = normalize_file(input_path, output_path)
        total_original += stats['original_bytes']
        total_normalized += stats['normalized_bytes']
        total_warnings += len(stats['warnings'])

        status = '⚠ ' if stats['warnings'] else '✓ '
        print(
            f"  {status}{stats['file']}: "
            f"{stats['original_bytes']:>8,} → {stats['normalized_bytes']:>8,} Bytes "
            f"({stats['reduction_pct']:>5.1f}% kleiner)"
        )
        for w in stats['warnings']:
            print(w)

    overall = round((1 - total_normalized / total_original) * 100, 1) if total_original else 0
    print(f'\nGesamt:   {total_original:,} → {total_normalized:,} Bytes ({overall}% Reduktion)')
    print(f'Warnungen: {total_warnings}')
    print(f'Output:    {output_dir}')


if __name__ == '__main__':
    main()
