# Feldpräsenz-Analyse — 26 Rechnungen (realtestdata_v2)
**Stand:** 27.04.2026 | **Basis:** output/normalized/realtestdata_v2/

> Prüft ob ein Feld im Markdown **vorhanden** ist — nicht ob es korrekt extrahiert wurde.
> Das ist die Grundlage um zu beurteilen wie hoch die theoretische Trefferquote sein kann.

> **Ausgeschlossen:** `sevdesk_musterrechnung` — kein echter Testfall (siehe unten).

---

## Übersichtstabelle

| Datei | RechNr | Datum | LeistDat | Lieferant | StNr | UStId | Empf. | Netto | MwSt% | MwSt€ | Brutto | IBAN | DokTyp |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Amazon | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| STRATO #1 | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| STRATO #2 | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| fernerofolio | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| billomat_gutschrift | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| billomat_kleinbetrag | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| billomat_standard | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| billomat_storno | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| congstar_Sep25 | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| congstar_Mrz26 | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| fastbill_gutschrift | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| fastbill_kleinbetrag | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| fastbill_standard | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| fastbill_storno | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| intersport | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| bluebrix | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| audible | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| lexoffice_gutschrift | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| lexoffice_kleinbetrag | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| lexoffice_standard | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| lexoffice_storno | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| sevdesk_gutschrift | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| sevdesk_kleinbetrag | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| sevdesk_standard | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| sevdesk_storno | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| word_template | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |

---

## Zusammenfassung: Theoretisches Maximum

| Feld | Im Markdown vorhanden | Max. erreichbare Quote | Aktuell extrahiert | Lücke | Bewertung |
|---|---|---|---|---|---|
| Rechnungsnummer | 20/26 (77%) | 77% | 25/26 (96%)* | — | Über Ceiling |
| Datum | 26/26 (100%) | 100% | 24/26 (92%) | 2 | Lösbar |
| Leistungsdatum | 15/26 (58%) | 58% | — | — | Nicht implementiert (Gruppe B) |
| Lieferant Name | 26/26 (100%) | 100% | 26/26 (100%) | — | Perfekt |
| Steuernummer | 17/26 (65%) | 65% | 17/26 (65%) | — | Am Ceiling |
| USt-IdNr | 16/26 (62%) | 62% | — | — | Nicht implementiert (Gruppe B) |
| Empfänger | 24/26 (92%) | 92% | — | — | Nicht implementiert (Gruppe B) |
| Nettobetrag | 23/26 (88%) | 88% | 21/26 (81%) | 2 | Lösbar |
| MwSt-Satz (%) | 24/26 (92%) | 92% | 23/26 (88%) | 1 | Fast am Ceiling |
| MwSt-Betrag | 24/26 (92%) | 92% | 21/26 (81%) | 3 | Lösbar |
| Bruttobetrag | 25/26 (96%) | 96% | 22/26 (85%) | 3 | Lösbar |
| IBAN | 21/26 (81%) | 81% | 21/26 (81%) | — | Am Ceiling |
| Dokumenttyp | 26/26 (100%) | 100% | 26/26 (100%) | — | Perfekt |

> *Rechnungsnummer: 96% > 77% weil die Rule Engine Formate findet die das Analyse-Script übersieht.

---

## Ausgeschlossen aus Testkorpus

**sevdesk_musterrechnung** — ausgeschlossen am 27.04.2026

Grund: Kein reales Dokument. sevDesk-Blanko-Template mit Platzhaltern (DD.MM.YYYY, XXXXX,
IBAN DEXX...) das nie durch einen echten Rechnungsstellungsprozess gelaufen ist.

Technische Ursache: Docling hat alle Wörter ohne Leerzeichen zusammengefügt
("MustermannKG-Musterstr.1-22222Musterstadt"). Das ist ein OCR-Parsing-Artefakt des
Template-Formats, kein Fehler der Rule Engine.

Dateien gelöscht:
- `output/normalized/realtestdata_v2/sevdesk_musterrechnung.md`
- `output/docling/realtestdata_v2/sevdesk_musterrechnung.md`

Original-PDF (falls vorhanden) bleibt in `samples/sevdesk/` erhalten.

---

## Beobachtungen

**Rechnungsnummer fehlt im Markdown (6 Dateien):**
Billomat (4×) — Docling packt Kopfzeile in Fließtext-Block ohne erkennbares Label.
Keine Lösung auf Regex-Ebene — braucht positionsbasierte Extraktion in Rule Engine.

**Leistungsdatum nur bei 58%:**
Viele einfache Rechnungen haben kein separates Leistungsdatum (= Rechnungsdatum).
Bei Jahresrechnungen (congstar) steht es als "Leistungszeitraum".

**USt-IdNr: Lexoffice und sevDesk tragen keine ein:**
Diese Tools lassen USt-IdNr weg wenn nur Steuernummer angegeben ist.
Beide Felder (StNr + UStId) sind alternative Pflichtangaben nach §14 UStG — eines reicht.

**congstar: kein MwSt-Satz und kein MwSt-Betrag erkennbar:**
congstar-Rechnungen haben MwSt pro Leistungsposition, nicht als Summe.
Gesamtsteuer steht in einer tief verschachtelten Tabelle die Docling nicht korrekt rendert.

**IBAN fehlt bei Amazon, fernerofolio, intersport, audible, word_template:**
Diese Lieferanten nutzen andere Zahlungswege (PayPal, Lastschrift, Kreditkarte).
Kein Fehler — IBAN ist dort schlicht nicht vorhanden.
