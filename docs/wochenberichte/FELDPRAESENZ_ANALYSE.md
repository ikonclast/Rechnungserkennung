# Feldpräsenz-Analyse — 27 Rechnungen (realtestdata_v2)
**Stand:** 26.04.2026 | **Basis:** output/normalized/realtestdata_v2/

> Prüft ob ein Feld im Markdown **vorhanden** ist — nicht ob es korrekt extrahiert wurde.
> Das ist die Grundlage um zu beurteilen wie hoch die theoretische Trefferquote sein kann.

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
| sevdesk_musterrechnung | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| sevdesk_standard | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| sevdesk_storno | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| word_template | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |

---

## Zusammenfassung: Theoretisches Maximum

| Feld | Im Markdown vorhanden | Max. erreichbare Quote | Aktuell extrahiert |
|---|---|---|---|
| Rechnungsnummer | 21/27 (78%) | 78% | 96%* |
| Datum | 27/27 (100%) | 100% | 93% |
| Leistungsdatum | 16/27 (59%) | 59% | 0% (nicht implementiert) |
| Lieferant Name | 27/27 (100%) | 100% | 0% (nicht implementiert) |
| Steuernummer | 18/27 (67%) | 67% | 0% (nicht implementiert) |
| USt-IdNr | 17/27 (63%) | 63% | 0% (nicht implementiert) |
| Empfänger | 25/27 (93%) | 93% | 0% (nicht implementiert) |
| Nettobetrag | 24/27 (89%) | 89% | 0% (nicht implementiert) |
| MwSt-Satz (%) | 25/27 (93%) | 93% | 0% (nicht implementiert) |
| MwSt-Betrag | 25/27 (93%) | 93% | 78% |
| Bruttobetrag | 26/27 (96%) | 96% | 81% |
| IBAN | 22/27 (81%) | 81% | 78% |
| Dokumenttyp | 27/27 (100%) | 100% | 0% (nicht implementiert) |

> *Rechnungsnummer: 96% > 78% weil die Rule Engine Formate findet die das Analyse-Script übersieht.

---

## Beobachtungen

**Rechnungsnummer fehlt im Markdown (6 Dateien):**
Billomat (4×) — Docling packt Kopfzeile in Fließtext-Block ohne erkennbares Label.
Keine Lösung auf Regex-Ebene — braucht positionsbasierte Extraktion in Rule Engine.

**Leistungsdatum nur bei 59%:**
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
