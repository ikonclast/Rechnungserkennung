# AGENTS.md

## Projektregel

Dieses Projekt folgt dem Leitfaden `docs/RECHNUNGSERKENNUNG_LEITFADEN.md`.

Aktueller Arbeitsbereich: **Wochen 3–4 (Baseline messen)** — Stand: 2026-04-25

---

## Fortschritt

### ✅ Wochen 1–2: Infrastruktur Setup — abgeschlossen

- [x] Git-Repo-Struktur aufgesetzt
- [x] Docker Compose für PostgreSQL + MinIO erstellt (`docker-compose.yml`)
- [x] Docling installiert und auf lokalen Test-Rechnungen getestet
- [x] Docling-Ergebnisse dokumentiert (`docs/DOCLING_TESTLAUF_WOCHE1.md`)

### 🔄 Wochen 3–4: Baseline messen — in Arbeit

- [x] Erste 21 echte deutsche Rechnungen verarbeitet (`samples/realtestdata/`)
- [x] Docling auf alle 21 Rechnungen angewendet, Output in `output/docling/realtestdata/`
- [x] **Top-10-Fehlerliste dokumentiert** (`docs/DOCLING_FEHLERLISTE_REALTESTDATA_WOCHE1.md`)
- [x] Analyse-Skript erstellt (`scripts/analyze_docling_outputs.py`)
- [ ] Datensatz auf 50 Rechnungen ausweiten (aktuell: 21)

**Lieferantentypen im Datensatz:** STRATO (5), congstar (7), Amazon (5), Audible (1), INTERSPORT (1), Stripe (1), sonstige (1)

**Kernerkenntnis aus der Fehlerliste:**
Docling ist als lokaler Parse-Layer technisch stabil und geeignet. Vor der Feldextraktion brauchen wir einen Normalisierungsschritt:
1. Base64-Bilder entfernen (betrifft 18/21 Dateien)
2. PDF-Separatoren (`=====`) bereinigen
3. Wiederholte Tabellenzellen deduplizieren
4. Gebrochene Datumslabels normalisieren

### ⏳ Wochen 5–10: Ingestion + Rule-Based Engine — noch nicht begonnen

---

## Erlaubte Arbeiten (Wochen 3–4)

- Docling-Output analysieren und dokumentieren
- Analyse-Skripte für Fehlermuster schreiben (`scripts/`)
- Normalisierungs-Prototyp für Docling-Markdown (Base64, Separatoren, Tabellen)
- Weitere Rechnungen in `samples/realtestdata/` hinzufügen und verarbeiten
- Wochenbericht erstellen (`docs/wochenberichte/`)

## Nicht bearbeiten (noch gesperrt)

- Keine FastAPI-App / Ingestion-API
- Keine Rule Engine
- Keine Datenbank-Migrationen für das finale Schema
- Keine UI
- Keine LLM-Integration
- Keine DATEV-Exporte

## Datenschutz

- Keine echten Rechnungen ins Git committen.
- Keine `.env` committen.
- Keine Mandantendaten an Cloud-KI senden.
- Testdaten liegen lokal in `samples/` und sind per `.gitignore` ausgeschlossen.

## Arbeitsweise

Vor Code immer kurz erklären:

1. Was wird geändert?
2. Warum wird es geändert?
3. Wie testen wir es?

Nach jeder Änderung:

1. Befehl zum Testen nennen
2. Erwartetes Ergebnis nennen
3. Commit-Vorschlag nennen