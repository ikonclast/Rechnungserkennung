# Skripte — Anleitung & Befehle

**Alle Befehle immer aus dem Projektroot ausführen:**
```
cd /home/tobias/rechnungserkennung
```

---

## Übersicht: 3 Skripte, 1 Reihenfolge

```
run_docling_batch.py       ← Schritt 1: PDFs → Markdown + JSON
normalize_docling_output.py ← Schritt 2: Markdown bereinigen
analyze_docling_outputs.py  ← Schritt 3: Felder auswerten, Fehler finden
```

---

## Schritt 1 — Docling Batch (`run_docling_batch.py`)

**Was es tut:** Läuft alle PDFs aus einem Ordner durch Docling und speichert pro PDF eine `.md` + `.json`.

**Befehl:**
```bash
.venv/bin/python scripts/run_docling_batch.py samples/realtestdata/ output/docling/realtestdata_v2/
```

**Output:**
```
output/docling/realtestdata_v2/
├── billomat_standard_001.md   ← Markdown (Tabellen, Text)
├── billomat_standard_001.json ← JSON (Docling-Rohstruktur, für Debugging)
├── ...
```

**Status:** Bereits gelaufen — 27 .md + 27 .json in `output/docling/realtestdata_v2/` (v2: inkl. PDF-Footer für IBAN/BIC)

---

## Schritt 2 — Normalisierung (`normalize_docling_output.py`)

**Was es tut:** Bereinigt die Markdown-Dateien — entfernt Base64-Bilder (Logos, QR-Codes) und `=====`-Trennlinien. Warnt wenn dabei wichtige Felder (Betrag, IBAN, Datum etc.) verloren gehen.

**Befehl:**
```bash
.venv/bin/python scripts/normalize_docling_output.py \
    output/docling/realtestdata_v2/ \
    output/normalized/realtestdata_v2/
```

**Output:**
```
output/normalized/realtestdata_v2/
├── billomat_standard_001.md   ← bereinigtes Markdown
├── ...
```

**Erwarteter Output im Terminal:**
```
  ✓ billomat_standard_001.md:   3.100 →   2.800 Bytes ( 9.7% kleiner)
  ✓ lexoffice_gutschrift_001.md: 4.200 →  1.100 Bytes (73.8% kleiner)
  ⚠ sevdesk_kleinbetrag_001.md: ...
    ⚠  IBAN-Signal verschwunden (IBAN)
```

Ein `⚠` bedeutet: Feld war im Original da, aber nach Bereinigung weg — solltest du prüfen.

---

## Schritt 3 — Analyse (`analyze_docling_outputs.py`)

**Was es tut:** Durchsucht die (normalisierten) Markdown-Dateien nach Rechnungsnummern, Daten, Beträgen, MwSt, IBAN. Dokumentiert welche Felder fehlen und wie oft.

**Befehl:**
```bash
.venv/bin/python scripts/analyze_docling_outputs.py output/normalized/realtestdata_v2/
```

**Output im Terminal:**
```
Analysiere 27 Dateien...

billomat_standard_001.md:
  ✓ Betrag:          €3.010,70
  ✓ Datum:           15.04.2026
  ✓ Rechnungsnummer: BIL-2026-001
  ✗ IBAN:            nicht gefunden
  ...
```

---

## Kurzfassung: alle 3 Schritte nacheinander

```bash
# Schritt 1 — Docling (bereits gelaufen, nur bei neuen PDFs nötig)
.venv/bin/python scripts/run_docling_batch.py \
    samples/realtestdata/ \
    output/docling/realtestdata_v2/

# Schritt 2 — Normalisieren
.venv/bin/python scripts/normalize_docling_output.py \
    output/docling/realtestdata_v2/ \
    output/normalized/realtestdata_v2/

# Schritt 3 — Analysieren
.venv/bin/python scripts/analyze_docling_outputs.py \
    output/normalized/realtestdata_v2/
```

---

## Warum immer `.venv/bin/python`?

Die `venv` ist der isolierte Python-Bereich des Projekts — nur dort ist `docling` installiert. Das System-Python (`python3`) kennt `docling` nicht und würde mit einem Fehler abbrechen.

```
.venv/bin/python   ← korrekt (docling installiert)
python3            ← falsch (kein docling)
```
