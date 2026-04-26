"""field_definitions.py

Definiert alle Extraktionsregeln pro Feld.
Jede Rule hat: Pattern, Confidence (0.0–1.0), Description (für Debugging).

Reihenfolge innerhalb eines Feldes: höchste Confidence zuerst.
Die Rule Engine probiert die Liste durch und nimmt den ersten Match.

Neue Regeln immer aus einem konkreten Fehler in top_10_errors.md ableiten —
keine spekulativen Patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    pattern: re.Pattern[str]
    confidence: float
    description: str


# ---------------------------------------------------------------------------
# Hilfsmuster (nicht direkt als Felder, aber in mehreren Regeln verwendet)
# ---------------------------------------------------------------------------

# Deutsches Geldbetragsformat: 1.142,40 € oder -57,12 €
_AMOUNT = r'(-?[\d]{1,3}(?:\.\d{3})*,\d{2})\s*(?:€|EUR)'

# EUR/€ vor der Zahl: € 82,85 / EUR 9.95 (Punkt oder Komma als Dezimaltrennzeichen)
_AMOUNT_EUR_FIRST = r'(?:€|EUR)\s*(-?[\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})'

# Deutsches Datum TT.MM.JJJJ
_DATE_DE = r'(\d{2}\.\d{2}\.\d{4})'


# ---------------------------------------------------------------------------
# RECHNUNGSNUMMER
# Quellen: top_10_errors.md — Fehler 2 (label_da_wert_nicht_extrahiert)
#          und Fehler 3 (kein_label_kein_format)
# ---------------------------------------------------------------------------

RECHNUNGSNUMMER: list[Rule] = [
    # Exaktes Label "Rechnungsnummer:" — höchste Sicherheit
    # Wert: Großbuchstabe oder Ziffer, dann min. 3 weitere Zeichen (verhindert "auf", "Seite")
    Rule(
        pattern=re.compile(r'Rechnungsnummer[:\s]+([A-Z0-9][A-Z0-9\-]{3,20})', re.IGNORECASE),
        confidence=0.95,
        description="label_rechnungsnummer_exakt",
    ),
    # Label-Variante "Rechnungs-Nr." (STRATO, congstar)
    Rule(
        pattern=re.compile(r'Rechnungs-Nr\.?[:\s]+([A-Z0-9][A-Z0-9\-]{3,20})', re.IGNORECASE),
        confidence=0.90,
        description="label_rechnungs_nr",
    ),
    # "Rechnung Nr.EM-2026-3" — Fastbill-Stil, kein Leerzeichen zwischen Label und Wert
    # "Gutschrift Nr. 2026-04-0825-G" — sevDesk Gutschrift
    Rule(
        pattern=re.compile(r'(?:Rechnung|Gutschrift)\s*Nr\.?\s*([A-Z0-9][A-Z0-9\-]{3,20})'),
        confidence=0.85,
        description="label_rechnung_gutschrift_nr",
    ),
    # "## Rechnung GH-2026-1847" oder "## Rechnungskorrektur GH-202" — Lexoffice (Nummer im Heading)
    Rule(
        pattern=re.compile(r'##\s*(?:Rechnung|Rechnungskorrektur)\s+([A-Z0-9][A-Z0-9\-]{3,20})\b'),
        confidence=0.85,
        description="label_rechnung_heading_lexoffice",
    ),
    # sevDesk-Sidebar: Label und Wert durch Zeilenumbruch getrennt
    # "RECHNUNGS-NR.\n\n2026-04-0815"
    Rule(
        pattern=re.compile(r'RECHNUNGS-NR\.?\s*\n+([A-Z0-9][A-Z0-9\-]{3,20})'),
        confidence=0.85,
        description="label_rechnungs_nr_sevdesk_sidebar",
    ),
    # Belegnummer-Label (alternative Bezeichnung bei manchen Tools)
    Rule(
        pattern=re.compile(r'Beleg(?:nummer|[-\s]?Nr\.?)[:\s]+([A-Z0-9][A-Z0-9\-]{3,20})', re.IGNORECASE),
        confidence=0.85,
        description="label_belegnummer",
    ),
    # Billomat-Format: YYYY-MMDD-NNN — Standard und Gutschrift (bis 5 Endziffern)
    # Nur nach "Rechnung" oder "Gutschrift" als Anker
    Rule(
        pattern=re.compile(r'(?:Rechnung|Gutschrift)\s+(\d{4}-\d{4}-\d{3,5})'),
        confidence=0.65,
        description="billomat_format_yyyy_mmdd_nnn",
    ),
    # Billomat Gutschrift/Storno: GS + Datum + Sequenz (z.B. GS20260417005)
    Rule(
        pattern=re.compile(r'\b(GS\d{11,13})\b'),
        confidence=0.70,
        description="billomat_format_gutschrift_gs",
    ),
    # congstar MA-Nummer (z.B. MA16657597) — Format-Pattern, kein Label im Markdown
    Rule(
        pattern=re.compile(r'\b(MA\d{8,})\b'),
        confidence=0.55,
        description="congstar_format_ma_nummer",
    ),
]


# ---------------------------------------------------------------------------
# DATUM (Rechnungsdatum)
# Ziel: das Rechnungsdatum, nicht Lieferdatum oder Fälligkeitsdatum
# ---------------------------------------------------------------------------

DATUM: list[Rule] = [
    # Exaktes Label "Rechnungsdatum:"
    Rule(
        pattern=re.compile(r'Rechnungsdatum[:\s]+' + _DATE_DE, re.IGNORECASE),
        confidence=0.95,
        description="label_rechnungsdatum",
    ),
    # "Datum: 15.04.2026" — Fastbill und viele andere
    Rule(
        pattern=re.compile(r'(?<!\w)Datum[:\s]+' + _DATE_DE, re.IGNORECASE),
        confidence=0.85,
        description="label_datum",
    ),
    # sevDesk-Sidebar: "DATUM\n\n15.04.2026"
    Rule(
        pattern=re.compile(r'DATUM\s*\n+' + _DATE_DE),
        confidence=0.85,
        description="label_datum_sevdesk_sidebar",
    ),
    # Erstes Datum im Dokument als Fallback — niedrige Confidence
    # weil es auch Lieferdatum oder Zahlungsziel treffen kann
    Rule(
        pattern=re.compile(_DATE_DE),
        confidence=0.50,
        description="datum_erstes_vorkommen_fallback",
    ),
]


# ---------------------------------------------------------------------------
# BETRAG BRUTTO (Gesamtbetrag inkl. MwSt)
# Bekannte Lücken: Gutschriften/Stornos haben andere Labels (Fehler 4)
# ---------------------------------------------------------------------------

BETRAG_BRUTTO: list[Rule] = [
    # "Endsumme\n\n1.142,40 €" oder "-57,12 €" — Fastbill (inkl. Gutschrift/Storno)
    Rule(
        pattern=re.compile(r'Endsumme\s*\n+' + _AMOUNT, re.IGNORECASE),
        confidence=0.95,
        description="label_endsumme_fastbill",
    ),
    # "## Gesamtbetrag brutto\n\n## 2.522,80 EUR" — sevDesk Standard/Kleinbetrag (Heading-Stil)
    Rule(
        pattern=re.compile(r'Gesamtbetrag\s+brutto\s*\n+(?:##\s*)?' + _AMOUNT, re.IGNORECASE),
        confidence=0.95,
        description="label_gesamtbetrag_brutto_heading",
    ),
    # "| Gesamtbetrag brutto | | | 252,28 EUR |" — sevDesk Gutschrift/Storno (Tabellen-Stil)
    Rule(
        pattern=re.compile(r'.*\bGesamtbetrag\s+brutto\b.*\|\s*' + _AMOUNT + r'\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.90,
        description="label_gesamtbetrag_brutto_tabelle",
    ),
    # "| Gesamtbetrag | Gesamtbetrag | ... | 1.048,39 |" — Lexoffice (wiederholte Zellen)
    # Greedy: nimmt den letzten numerischen Wert in der Zeile
    Rule(
        pattern=re.compile(r'.*\bGesamtbetrag\b.*\|\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.85,
        description="label_gesamtbetrag_tabelle_letzte_zelle",
    ),
    # "Gesamt brutto: ... 3.010,70 €" — Billomat
    Rule(
        pattern=re.compile(r'Gesamt\s+brutto[:\s|]+.*?' + _AMOUNT, re.IGNORECASE),
        confidence=0.85,
        description="label_gesamt_brutto_billomat",
    ),
    # "| Summe Rechnungsbetrag | EUR | 31,00 |" — STRATO
    Rule(
        pattern=re.compile(r'\|\s*Summe Rechnungsbetrag\s*\|\s*EUR\s*\|\s*([\d.,]+)\s*\|'),
        confidence=0.90,
        description="label_summe_rechnungsbetrag_strato",
    ),
    # "| Rechnungsbetrag: | ... | € 82,85 |" — intersport (EUR vor Zahl, wiederholte Zellen)
    Rule(
        pattern=re.compile(r'.*\bRechnungsbetrag\b.*\|\s*' + _AMOUNT_EUR_FIRST + r'\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.85,
        description="label_rechnungsbetrag_tabelle_eur_first",
    ),
    # "Im Gesamtbetrag von 25,00 EUR" — bluebrix
    Rule(
        pattern=re.compile(r'Gesamtbetrag\s+von\s+([\d]{1,3}(?:\.\d{3})*,\d{2})\s*(?:€|EUR)', re.IGNORECASE),
        confidence=0.85,
        description="label_gesamtbetrag_von_bluebrix",
    ),
    # "Gesamt: €214,20" — Word-Template (€ vor Zahl, Doppelpunkt)
    Rule(
        pattern=re.compile(r'Gesamt:\s*' + _AMOUNT_EUR_FIRST, re.IGNORECASE),
        confidence=0.85,
        description="label_gesamt_eur_first_word",
    ),
    # "Zahlbetrag\n\nEUR 9.95" — Audible (EUR vor Zahl, Punkt als Dezimaltrennzeichen)
    Rule(
        pattern=re.compile(r'Zahlbetrag\s*\n+' + _AMOUNT_EUR_FIRST, re.IGNORECASE),
        confidence=0.90,
        description="label_zahlbetrag_eur_first_audible",
    ),
    # "Rechnungsbetrag" generisch
    Rule(
        pattern=re.compile(r'Rechnungsbetrag[:\s]+' + _AMOUNT, re.IGNORECASE),
        confidence=0.80,
        description="label_rechnungsbetrag_generisch",
    ),
    # Gutschrift/Storno-Labels
    Rule(
        pattern=re.compile(r'Gutschriftsbetrag[:\s]+' + _AMOUNT, re.IGNORECASE),
        confidence=0.90,
        description="label_gutschriftsbetrag",
    ),
    Rule(
        pattern=re.compile(r'Stornobetrag[:\s]+' + _AMOUNT, re.IGNORECASE),
        confidence=0.90,
        description="label_stornobetrag",
    ),
]


# ---------------------------------------------------------------------------
# MWST_BETRAG (der absolute MwSt-Betrag, nicht der Prozentsatz)
# ---------------------------------------------------------------------------

MWST_BETRAG: list[Rule] = [
    # "zzgl. 19,00% MwSt. 182,40 €" oder "-9,12 €" — Fastbill (inkl. Gutschrift/Storno)
    Rule(
        pattern=re.compile(r'zzgl\.\s*[\d,]+\s*%\s*MwSt\.?\s+' + _AMOUNT, re.IGNORECASE),
        confidence=0.95,
        description="label_zzgl_mwst_fastbill",
    ),
    # "| Umsatzsteuer (19,00%) | EUR | 4,95 |" — STRATO
    Rule(
        pattern=re.compile(r'\|\s*Umsatzsteuer\s*\([^)]+\)\s*\|\s*EUR\s*\|\s*([\d.,]+)\s*\|'),
        confidence=0.95,
        description="label_umsatzsteuer_strato",
    ),
    # "| Umsatzsteuer 19% | Umsatzsteuer 19% | ... | 167,39 |" — Lexoffice (wiederholte Zellen, kein €)
    Rule(
        pattern=re.compile(r'.*\bUmsatzsteuer\s+\d+\s*%.*\|\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.90,
        description="label_umsatzsteuer_pct_tabelle",
    ),
    # "| Umsatzsteuer 19% | | | 402,80 EUR |" — sevDesk (Tabellen-Stil)
    Rule(
        pattern=re.compile(r'.*\bUmsatzsteuer\s+\d+\s*%.*\|\s*' + _AMOUNT + r'\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.90,
        description="label_umsatzsteuer_pct_tabelle_eur",
    ),
    # "| USt 19 %(2.530,00 €): | ... | 480,70 € |" — Billomat (wiederholte Zellen, € am Ende)
    Rule(
        pattern=re.compile(r'.*\bUSt\s+\d+\s*%[^|]*\|\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*€\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.90,
        description="label_ust_pct_tabelle_billomat",
    ),
    # "| zzgl.19% MwSt. auf € 82,85 | ... | € 13,23 |" — intersport (wiederholte Zellen, € vor Wert)
    Rule(
        pattern=re.compile(r'.*zzgl\.\s*\d+%\s*MwSt.*\|\s*€\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.90,
        description="label_zzgl_mwst_tabelle_eur_first",
    ),
    # "19,0 % MwSt. = 3,99 EUR" — bluebrix (eingebettet in Satz)
    Rule(
        pattern=re.compile(r'[\d,]+\s*%\s*MwSt\.?\s*=\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*(?:€|EUR)', re.IGNORECASE),
        confidence=0.90,
        description="label_mwst_gleichzeichen_bluebrix",
    ),
    # "MwSt (19%): €34,20" — Word-Template (€ vor Zahl, Klammer)
    Rule(
        pattern=re.compile(r'MwSt\s*\([^)]*\)[:\s]*' + _AMOUNT_EUR_FIRST, re.IGNORECASE),
        confidence=0.90,
        description="label_mwst_klammer_word",
    ),
    # "| 7% | (ohne USt.) 9.30 | 0.65 |" — Audible (Englisches Dezimalformat mit Punkt)
    Rule(
        pattern=re.compile(r'\|\s*\d+%\s*\|[^|]+\|\s*([\d]+\.\d{2})\s*\|'),
        confidence=0.75,
        description="label_ust_pct_audible_en",
    ),
]


# ---------------------------------------------------------------------------
# IBAN
# Zuverlässigstes Feld — IBAN-Format ist normiert (ISO 13616)
# ---------------------------------------------------------------------------

IBAN: list[Rule] = [
    # "IBAN DE26 3804..." oder "IBAN: DE26..." — Standard-Label
    Rule(
        pattern=re.compile(r'IBAN[:\s]+([A-Z]{2}\d{2}[\s\d]{15,32})', re.IGNORECASE),
        confidence=0.99,
        description="label_iban",
    ),
    # sevDesk-Sidebar v1: "I B A N\n\nDE75 6725..."
    Rule(
        pattern=re.compile(r'I\s+B\s+A\s+N\s*\n+([A-Z]{2}\d{2}[\s\d]{15,32})'),
        confidence=0.95,
        description="label_iban_sevdesk_sidebar_spaced",
    ),
    # sevDesk v2 Footer: "BANK\nDE75672500200062222558" — kein IBAN-Label, direkt nach BANK
    Rule(
        pattern=re.compile(r'BANK\s*\n+([A-Z]{2}\d{20,22})\b'),
        confidence=0.85,
        description="label_iban_nach_bank_sevdesk",
    ),
]


# ---------------------------------------------------------------------------
# Alle Felder — wird von rule_engine.py importiert
# ---------------------------------------------------------------------------

ALL_FIELDS: dict[str, list[Rule]] = {
    "rechnungsnummer": RECHNUNGSNUMMER,
    "datum":           DATUM,
    "betrag_brutto":   BETRAG_BRUTTO,
    "mwst_betrag":     MWST_BETRAG,
    "iban":            IBAN,
}
