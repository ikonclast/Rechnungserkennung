# Projektstand — KW17 / Woche 5-6
**Stand:** 26.04.2026 | **Phase:** Woche 5–6 (Rule Engine)

---

## Was bisher erledigt ist

### Woche 1–2: Infrastruktur
- [x] Git-Repo, Docker Compose (PostgreSQL + MinIO)
- [x] Docling installiert und getestet

### Woche 3–4: Baseline messen
- [x] 27 echte Rechnungen gesammelt (4 Billing-Tools × 4 Szenarien + 7 Lieferanten)
- [x] Docling-Batch auf alle 27 PDFs — `output/docling/realtestdata_v2/`
- [x] Normalisierung — `output/normalized/realtestdata_v2/`
- [x] Top-10-Fehler dokumentiert — `output/analysis/top_10_errors.md`

### Woche 5–6: Rule Engine (laufend)
- [x] `src/extraction/field_definitions.py` — Regex-Regeln mit Confidence-Scores
- [x] `src/extraction/rule_engine.py` — Extraktion aus normalisiertem Markdown
- [x] Docling-Bug gefixt: `PAGE_FOOTER` / `FURNITURE`-Layer fehlte → IBAN-Rate 19% → 78%

---

## Aktuelle Extraktionsraten (27 Rechnungen, realtestdata_v2)

| Feld | Treffer | Quote | Bewertung |
|---|---|---|---|
| Rechnungsnummer | 26/27 | 96% | ✅ produktionsreif |
| Datum | 25/27 | 93% | ✅ produktionsreif |
| Betrag brutto | 22/27 | 81% | ✅ solide |
| MwSt-Betrag | 21/27 | 78% | ✅ solide |
| IBAN | 21/27 | 78% | ✅ solide (alle die im PDF stehen) |

---

## Fehlende Felder — noch einzubauen (§14 UStG Pflichtangaben)

Diese Felder fehlen noch in `field_definitions.py`:

| Feld | Warum wichtig | Priorität |
|---|---|---|
| **Nettobetrag** | Buchungsbetrag auf Sachkonto | Hoch |
| **MwSt-Satz (%)** | DATEV-Buchungsschlüssel (19%→9, 7%→2) | Hoch |
| **Leistungsdatum** | Oft ≠ Rechnungsdatum, §14 Pflicht | Hoch |
| **Lieferant (Name)** | Ohne Absender keine Buchungszuordnung | Hoch |
| **Steuernummer / USt-IdNr.** | Vorsteuerabzug hängt daran | Hoch |
| Empfänger (Name) | §14 Pflicht, für Multi-Mandant | Mittel |

---

## Bekannte Limitierungen / Offene Punkte

| Problem | Ursache | Status |
|---|---|---|
| bluebrix Rechnungsnummer fehlt | Docling macht Spaltenheader draus, kein Wert | Docling-Limit, akzeptiert |
| congstar IBAN maskiert | Absichtlich von congstar anonymisiert | Nicht lösbar |
| Amazon/fernerofolio Betrag fehlt | Kein erkennbares Label im Markdown | Docling-Limit |
| sevdesk_gutschrift IBAN 1 Stelle zu lang | Leerzeichen-Stripping-Artefakt | Kleiner Pattern-Fix offen |

---

## Nächste Schritte (in dieser Reihenfolge)

```
Woche 5-6 Restarbeit:
  → Fehlende Felder in field_definitions.py (Netto, MwSt-Satz, Leistungsdatum, Lieferant, StNr)
  → Abschlusstest: alle Felder auf 27 Rechnungen

Woche 7-8: Datenbankschema
  → append-only PostgreSQL, Audit-Log, Trigger
  → Tabellen: documents, extractions, validations, confirmations, audit_log

Woche 7-8: Ingestion Service
  → Upload → SHA-256 → MinIO → DB-Eintrag
  → src/ingestion/pipeline.py, hasher.py, storage.py

Woche 9-10: Alles verbinden
  → Rule Engine → DB-Schreibung
  → Validierung (IBAN-Prüfsumme, MwSt-Rechenkontrolle, §14-Check)

Woche 11-16: Review UI + Validation Layer
  → Human-in-the-Loop erzwingen
  → Confidence sichtbar machen
  → Tool-Vergleich Docling vs. Alternative (IBAN-Footer-Problem dokumentiert)
```

---

## Dateistruktur aktuell

```
rechnungserkennung/
├── samples/realtestdata/          27 PDF-Rechnungen
├── output/
│   ├── docling/realtestdata_v2/   27 .md + 27 .json (mit FURNITURE-Layer)
│   ├── normalized/realtestdata_v2/ 27 bereinigte .md (Arbeitsgrundlage)
│   └── analysis/top_10_errors.md  Fehleranalyse für Rule Engine
├── src/extraction/
│   ├── field_definitions.py       Regex-Regeln + Confidence-Scores
│   └── rule_engine.py             Extraktion aus Markdown
└── scripts/
    ├── run_docling_batch.py        Schritt 1: PDF → Markdown
    ├── normalize_docling_output.py Schritt 2: Bereinigung
    └── analyze_docling_outputs.py  Schritt 3: Diagnose + top_10_errors.md
```

---

## Wichtige Erkenntnisse dieser Phase

1. **Docling verliert PAGE_FOOTER standardmäßig** — FURNITURE-Layer muss explizit eingeschlossen werden. Fix in `run_docling_batch.py` eingepflegt.
2. **Format-Patterns allein reichen nicht** — Label-relative Extraktion ist robuster. Rechnungsnummer-Rate von 44% auf 96% durch Label-Patterns.
3. **Analyse-Script ≠ Rule Engine** — Keyword-Präsenz (85% Betrag im Analyse-Script) sagt nichts über Extrahierbarkeit (33% vor Fixes). Immer beide messen.
4. **MwSt = USt = Mehrwertsteuer** — gleicher Steuertyp, verschiedene Bezeichnungen je Lieferant.
