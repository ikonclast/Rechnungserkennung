# Felddefinitionen — Was wirklich gebraucht wird
**Stand:** 02.05.2026 | **Zielgruppe:** Steuerberater / DATEV-Anbindung / GoBD-Konformität

---

## 1. Rechtsgrundlagen

### §14 UStG — Pflichtangaben auf einer Rechnung

Ohne diese Felder ist eine Rechnung steuerrechtlich **ungültig** — kein Vorsteuerabzug möglich:

| Nr. | Pflichtangabe | Unser Feld |
|---|---|---|
| 1 | Vollständiger Name + Anschrift des **Lieferanten** | `lieferant_name`, `lieferant_adresse` |
| 2 | Vollständiger Name + Anschrift des **Empfängers** | `empfaenger_name` |
| 3 | **Steuernummer** ODER **USt-IdNr.** des Lieferanten | `steuernummer` / `ust_idnr` |
| 4 | **Ausstellungsdatum** (Rechnungsdatum) | `datum` ✅ |
| 5 | Fortlaufende **Rechnungsnummer** | `rechnungsnummer` ✅ |
| 6 | Menge + Art der Leistung (**Positionsbeschreibung**) | `positionen` — nur Woche 11+ |
| 7 | **Zeitpunkt der Lieferung/Leistung** (Leistungsdatum) | `leistungsdatum` |
| 8 | **Nettobetrag** je Steuersatz aufgegliedert | `nettobetrag` |
| 9 | Vereinbarte Entgeltsminderungen (Skonto, Rabatt) | `skonto` — nice to have |
| 10 | **MwSt-Satz** (%) + **MwSt-Betrag** (€) | `mwst_satz`, `mwst_betrag` ✅ |
| 11 | Bei Steuerbefreiung: Hinweis | Sonderfall, Phase 2 |

### §33 UStDV — Kleinbetragsrechnung (bis €250 Brutto)

Erleichterte Anforderungen — **keine Rechnungsnummer, kein Empfänger** Pflicht:
- Lieferant Name + Adresse
- Datum
- Menge + Art der Leistung
- Bruttobetrag + Steuersatz ODER Bruttobetrag + Steuerbetrag

**Konsequenz für uns:** Das System muss den Dokumenttyp + Bruttobetrag kennen,
um zu entscheiden welche Felder als Pflicht zu prüfen sind.

### GoBD — Grundsätze zur ordnungsmäßigen Buchführung

| Anforderung | Technische Umsetzung |
|---|---|
| Unveränderlichkeit | Append-only DB, kein UPDATE/DELETE |
| Vollständigkeit | Alle Pflichtfelder vor Bestätigung prüfen |
| Nachvollziehbarkeit | Audit-Log bei jeder Aktion (Trigger) |
| 10 Jahre Aufbewahrung | `retain_until` Feld + MinIO Object-Lock |
| Maschinelle Auswertbarkeit | Strukturierte DB-Felder, kein Freitext |

---

## 2. Was der Steuerberater zum Buchen braucht (DATEV)

Ein DATEV-Buchungssatz besteht aus:

```
Buchungsdatum | Belegnummer | Betrag (Netto) | Steuercode | Gegenkonto | Buchungstext
```

| DATEV-Feld | Kommt aus | Beispiel |
|---|---|---|
| Buchungsdatum | `leistungsdatum` (bevorzugt) oder `datum` | 15.04.2026 |
| Belegnummer | `rechnungsnummer` | EM-2026-3 |
| Betrag Netto | `nettobetrag` | 960,00 |
| Steuercode | abgeleitet aus `mwst_satz` | 19% → Code 9 |
| Gegenkonto | `lieferant_name` (Kreditorenkonto) | Elektro Müller GmbH |
| Buchungstext | `lieferant_name` + ggf. Positionsbeschreibung | Elektro Müller GmbH |

**DATEV-Steuercodes (die wichtigsten):**

| MwSt-Satz | DATEV-Code | Bedeutung |
|---|---|---|
| 19% | 9 | Regelsteuersatz Vorsteuer |
| 7% | 2 | Ermäßigter Steuersatz Vorsteuer |
| 0% | 40 | Steuerfreie Eingangsleistung |
| Reverse Charge | 84/85 | Steuerschuldumkehr (§13b UStG) |

---

## 3. Vollständige Feldliste für unser System

### Gruppe A — Pflicht (MVP, ohne das kein Pilot)

**Feldkanon eingefroren ab 02.05.2026 — kein neues Feld bis Phase 2.**

| Feld | Typ | §14 | GoBD | DATEV | Priorität |
|---|---|:---:|:---:|:---:|---|
| `rechnungsnummer` | String | ✅ | ✅ | ✅ | **Implementiert** |
| `datum` | Date | ✅ | ✅ | ✅ | **Implementiert** |
| `betrag_brutto` | Decimal | — | ✅ | — | **Implementiert** |
| `mwst_betrag` | Decimal | ✅ | ✅ | ✅ | **Implementiert** |
| `iban` | String | — | — | ✅ | **Implementiert** |
| `dokumenttyp` | Enum | — | ✅ | ✅ | **Implementiert** |
| `netto_betrag` | Decimal | ✅ | ✅ | ✅ | **Implementiert** |
| `mwst_satz` | Decimal | ✅ | ✅ | ✅ | **Implementiert** |
| `lieferant_name` | String | ✅ | ✅ | ✅ | **Implementiert** |
| `steuernummer` | String | ✅* | ✅ | — | **Implementiert** |
| `ust_idnr` | String | ✅* | ✅ | — | **Implementiert — B1.1** |
| `leistungsdatum` | Date | ✅ | — | ✅ | **Implementiert — B1.2** |

> *Steuernummer ODER USt-IdNr. — eines von beiden reicht für §14 Abs. 4 Nr. 3.
> Wenn `leistungsdatum` fehlt: DATEV-Export verwendet `datum` als Fallback (dokumentiert).

### Gruppe B — Phase 2 (nach dem Pilot)

| Feld | Typ | §14 | Anmerkung |
|---|---|:---:|---|
| `empfaenger_name` | String | ✅ | Phase 2 — Pilot ist Single-User |
| `lieferant_adresse` | String | ✅ | Phase 2 — für §14 vollständig |

### Gruppe C — Sinnvoll (für Operations und Phase 2)

| Feld | Typ | Anmerkung |
|---|---|---|
| `zahlungsziel` | Date | Für Mahnwesen und Liquiditätsplanung |
| `skonto_satz` | Decimal | §14 Abs. 4 Nr. 9 — nur wenn vereinbart |
| `bic` | String | Zahlungsabwicklung |
| `waehrung` | String | Für internationale Rechnungen (Standard: EUR) |
| `positionen` | JSON-Array | §14 Nr. 6 — für Phase 2 (Review UI) |

### Gruppe D — Phase 2 / Nice to have

| Feld | Anmerkung |
|---|---|
| `kostenstelle` | Selten auf Rechnungen, meist manuell |
| `buchungskonto` | Automatisierung durch Lieferant-Zuordnung |
| `steuerbefreiung_grund` | §14 Abs. 4 Nr. 8 — Sonderfall |
| `reverse_charge` | §13b UStG — B2B EU-Ausland |

---

## 4. Dokumenttypen — kritisch für korrekte Buchung

Das System **muss** den Dokumenttyp kennen — eine Gutschrift hat negatives Vorzeichen:

| Typ | Bedeutung | Buchung | Erkennungsmerkmal |
|---|---|---|---|
| `rechnung` | Normale Ausgangsrechnung | Positiv | Default |
| `gutschrift` | Entlastung/Rückerstattung | **Negativ** | "Gutschrift", "Rechnungskorrektur" |
| `storno` | Vollständige Umkehrung | **Negativ** | "Storno", "GS"-Prefix |
| `kleinbetragsrechnung` | §33 UStDV, ≤€250 | Positiv | Brutto ≤ 250€ + keine RechNr-Pflicht |
| `anzahlung` | Vorauszahlung | Positiv | "Anzahlung", "Abschlag" |

---

## 5. Was wir NICHT extrahieren müssen (Begründung)

| Feld | Warum nicht |
|---|---|
| Positionsbeschreibungen (Freitext) | Kein Mehrwert für Buchung; Steuerberater schaut ins Original-PDF |
| Lieferbedingungen (Incoterms) | Nur relevant für Importeure/Exporteure |
| Bankname | IBAN allein reicht für Überweisung |
| Bestellnummer | Optional; wenn vorhanden in `rechnungsnummer` mitspeichern |
| Kundennummer beim Lieferanten | Kein buchhalterischer Wert |

---

## 6. §14-Validierungslogik (für Woche 9-10)

Bevor eine Rechnung als "buchbar" markiert wird, muss das System prüfen:

```python
def validate_paragraph14(doc) -> list[str]:
    errors = []

    # Pflicht für alle Rechnungstypen
    if not doc.lieferant_name:   errors.append("§14(1): Lieferant fehlt")
    if not doc.datum:            errors.append("§14(4): Rechnungsdatum fehlt")
    if not doc.netto_betrag:     errors.append("§14(8): Nettobetrag fehlt")
    if not doc.mwst_satz:        errors.append("§14(10): MwSt-Satz fehlt")
    if not (doc.steuernummer or doc.ust_idnr):
                                 errors.append("§14(3): StNr/UStId fehlt")

    # Nur bei Normalrechnung (nicht Kleinbetragsrechnung)
    if doc.dokumenttyp != "kleinbetragsrechnung":
        if not doc.rechnungsnummer: errors.append("§14(5): Rechnungsnummer fehlt")
        if not doc.empfaenger_name: errors.append("§14(2): Empfänger fehlt")

    return errors
```

---

## 7. Fazit: Implementierungsreihenfolge

```
Woche 5-6 (jetzt):
  1. dokumenttyp     — Erkennung Rechnung/Gutschrift/Storno (kritisch für Vorzeichen)
  2. netto_betrag    — Buchungsgrundlage
  3. mwst_satz       — DATEV-Buchungsschlüssel
  4. lieferant_name  — Gegenkonto in DATEV
  5. steuernummer    — §14 Vorsteuerabzug

Woche 5-6 (wenn Zeit):
  6. ust_idnr        — Alternative zu StNr
  7. leistungsdatum  — Buchungsdatum in DATEV
  8. empfaenger_name — §14 + Multi-Mandant

Woche 9-10 (Validation Layer):
  9. §14-Vollständigkeitsprüfung
  10. MwSt-Rechenkontrolle (netto × satz = betrag ±1ct)
  11. IBAN-Prüfsumme

Phase 2:
  12. positionen (Einzelpositionen)
  13. DATEV-Export mit korrekten Buchungsschlüsseln
```
