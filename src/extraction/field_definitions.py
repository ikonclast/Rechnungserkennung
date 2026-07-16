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
    fixed_value: str | None = None  # wenn gesetzt, wird dieser Wert statt group(1) zurückgegeben


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
    # bluebrix Sidebar: Label und Wert durch mehrere Zeilen getrennt (Datum+Kdnr dazwischen)
    # Mindestens 8 Ziffern — überspringt 6-stellige Kundennummer "999856"
    Rule(
        pattern=re.compile(r'Rechnungsnummer\s*\n+(?:[^\n]*\n)*?(\d{8,12})\b'),
        confidence=0.60,
        description="label_rechnungsnummer_sidebar_bluebrix",
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
    # Amazon DE: "Rechnungsdatum\n/Lieferdatum\n\n28.12.2025" — Label auf separater Zeile, DE-Datum
    # Auch: reines "Rechnungsdatum\n\n28.12.2025" ohne Lieferdatum-Suffix
    Rule(
        pattern=re.compile(
            r'Rechnungsdatum\s*\n+(?:/\s*Lieferdatum\s*\n+)?'
            r'(\d{2}\.\d{2}\.\d{4})',
            re.IGNORECASE,
        ),
        confidence=0.90,
        description="label_rechnungsdatum_newline_de",
    ),
    # SevDesk Gutschrift/Storno-Sidebar: "Gutschrift-Nr. Datum Leistungszeitraum\n{nr}\n{datum}"
    # Docling rendert mehrspaltige Sidebar mit Labels in Zeile 1, Werte in Folgezeilen.
    Rule(
        pattern=re.compile(
            r'Gutschrift-Nr\.\s+Datum\s+Leistungszeitraum\s*\n+'
            r'\S+\s*\n+'
            r'(\d{2}\.\d{2}\.\d{4})',
        ),
        confidence=0.87,
        description="label_datum_sevdesk_gutschrift_storno",
    ),
    # "Datum: 15.04.2026" — Fastbill und viele andere (Label + Wert in einer Zeile)
    Rule(
        pattern=re.compile(r'(?<!\w)Datum[:\s]+' + _DATE_DE, re.IGNORECASE),
        confidence=0.85,
        description="label_datum",
    ),
    # sevDesk-Standard-Sidebar: "DATUM\n\n15.04.2026"
    Rule(
        pattern=re.compile(r'DATUM\s*\n+' + _DATE_DE),
        confidence=0.85,
        description="label_datum_sevdesk_sidebar",
    ),
    # Lexoffice Sidebar: "Datum:\n{nicht-Datum-Zeilen}\n\nDD.MM.YYYY"
    # Docling trennt 2-Spalten-Sidebar: erst alle Labels, dann alle Werte.
    # Überspringt Rechnungsnr/Kundennr und landet auf erstem Datum.
    Rule(
        pattern=re.compile(
            r'Datum:\s*\n+'
            r'(?:(?!\d{2}\.\d{2}\.\d{4})[^\n]+\n+)*'
            r'(\d{2}\.\d{2}\.\d{4})',
        ),
        confidence=0.85,
        description="label_datum_sidebar_lexoffice",
    ),
    # Congstar: "Rechnungsdatum Rechnungsnummer Seite Mandats-ID\n{kundennr} {datum} ..."
    # Alle Labels in einer Zeile, danach Werte in gleicher Reihenfolge.
    Rule(
        pattern=re.compile(
            r'Rechnungsdatum\s+Rechnungsnummer\s+[^\n]*\n+'
            r'\w+\s+(\d{2}\.\d{2}\.\d{4})',
        ),
        confidence=0.85,
        description="label_datum_congstar_sidebar",
    ),
    # BlueBrix Sidebar: "Datum\nKundennummer\nRechnungsnummer\n{datum}\n..."
    Rule(
        pattern=re.compile(
            r'(?<!\w)Datum\s*\n+Kundennummer\s*\n+Rechnungsnummer\s*\n+'
            r'(\d{2}\.\d{2}\.\d{4})',
        ),
        confidence=0.85,
        description="label_datum_bluebrix_sidebar",
    ),
    # Fernerofolio: "Ausstellungsdatum\n\n25. Dezember 2025" — kein DE-Datumsformat.
    # Nächstes DD.MM.YYYY (aus Produkttabelle) ist das gleiche Datum.
    Rule(
        pattern=re.compile(
            r'Ausstellungsdatum\s+'
            r'(?:(?!\d{2}\.\d{2}\.\d{4})[\s\S])*?'
            r'(\d{2}\.\d{2}\.\d{4})',
        ),
        confidence=0.82,
        description="label_ausstellungsdatum_voraus",
    ),
    # intersport: "Rechnungsdatum March 26, 2026" — englisches Datum in Tabellenzelle
    Rule(
        pattern=re.compile(
            r'Rechnungsdatum\s+'
            r'((?:January|February|March|April|May|June|July|August|September|October|November|December)'
            r'\s+\d{1,2},?\s+\d{4})',
            re.IGNORECASE,
        ),
        confidence=0.85,
        description="label_rechnungsdatum_english_full",
    ),
    # audible: "Rechnungsdatum\n/Lieferdatum\n\n09 Apr 2026" — abgekürzter englischer Monat
    Rule(
        pattern=re.compile(
            r'Rechnungsdatum\s*\n+(?:/\s*Lieferdatum\s*\n+)?'
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
            re.IGNORECASE,
        ),
        confidence=0.85,
        description="label_rechnungsdatum_english_abbr",
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
    # "Zahlbetrag\n\n9,34 €" — Amazon (EUR nach Zahl, deutsches Format)
    Rule(
        pattern=re.compile(r'Zahlbetrag\s*\n+' + _AMOUNT, re.IGNORECASE),
        confidence=0.90,
        description="label_zahlbetrag_eur_after_amazon",
    ),
    # "## 164,99 € fällig am" — fernerofolio (Betrag im Heading vor "fällig")
    Rule(
        pattern=re.compile(r'##\s+([\d]{1,3}(?:\.\d{3})*,\d{2})\s*€\s+fällig\b'),
        confidence=0.88,
        description="label_betrag_heading_faellig_fernerofolio",
    ),
    # "58,00 €\n\n## Zu zahlender Betrag:" — congstar (Betrag steht vor dem Label)
    Rule(
        pattern=re.compile(r'([\d]{1,3}(?:\.\d{3})*,\d{2})\s*€\s*\n+##\s*Zu\s+zahlender\s+Betrag', re.IGNORECASE),
        confidence=0.88,
        description="label_zu_zahlender_betrag_congstar",
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
    # "| USt. - Deutschland 19 % inkl. ... | 26,34 € |" — fernerofolio (wiederholte Zellen, €-Suffix)
    Rule(
        pattern=re.compile(r'.*\bUSt\.\s*-\s*Deutschland\s+\d+\s*%.*\|\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*€\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.90,
        description="label_ust_deutschland_betrag_tabelle",
    ),
    # "| USt. Gesamt | ... | 7,85 € | 1,49 € |" — Amazon (letzter Wert = MwSt-Betrag)
    Rule(
        pattern=re.compile(r'.*\bUSt\.?\s+Gesamt\b.*\|\s*([\d]+,\d{2})\s*€\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.88,
        description="label_ust_gesamt_mwst_amazon",
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
# DOKUMENTTYP (Enum: rechnung | gutschrift | storno | kleinbetragsrechnung)
# Reihenfolge: Storno vor Gutschrift — sevDesk-Storno trägt beides im Text.
# Kleinbetragsrechnung und Default "rechnung" via Cross-Field-Logik in rule_engine.py.
# ---------------------------------------------------------------------------

DOKUMENTTYP: list[Rule] = [
    # Storno — explizites Keyword: "Storno wegen..." / "STORNO: ..." (fastbill, billomat, sevDesk, lexoffice)
    Rule(
        pattern=re.compile(r'\bStorno\b', re.IGNORECASE),
        confidence=0.92,
        description="keyword_storno",
        fixed_value="storno",
    ),
    # Storno — Billomat GS-Nummernpräfix (GS + 11–13 Ziffern)
    Rule(
        pattern=re.compile(r'\bGS\d{11,13}\b'),
        confidence=0.85,
        description="billomat_gs_prefix_storno",
        fixed_value="storno",
    ),
    # Gutschrift — Heading "## Gutschrift Nr." / "Gutschrift Nr." (sevDesk-Gutschrift)
    Rule(
        pattern=re.compile(r'(?:##\s*)?Gutschrift\s+Nr\.?', re.IGNORECASE),
        confidence=0.95,
        description="label_gutschrift_nr",
        fixed_value="gutschrift",
    ),
    # Gutschrift — Lexoffice "## Rechnungskorrektur"
    Rule(
        pattern=re.compile(r'Rechnungskorrektur', re.IGNORECASE),
        confidence=0.90,
        description="label_rechnungskorrektur",
        fixed_value="gutschrift",
    ),
    # Gutschrift — allgemeines Keyword (fastbill Hinweis, billomat-Gutschrift Titel)
    Rule(
        pattern=re.compile(r'\bGutschrift\b', re.IGNORECASE),
        confidence=0.78,
        description="keyword_gutschrift",
        fixed_value="gutschrift",
    ),
    # Kleinbetragsrechnung + Default "rechnung" → in rule_engine.py als Cross-Field-Logik
]


# ---------------------------------------------------------------------------
# NETTO_BETRAG (Zwischensumme netto / Gesamtbetrag netto)
# Quellen: je nach Tool unterschiedliche Labels und Formatierungen
# ---------------------------------------------------------------------------

NETTO_BETRAG: list[Rule] = [
    # sevDesk: "| Gesamtbetrag netto | ... | 2.120,00 EUR |" (Tabelle, wiederholte Zellen)
    Rule(
        pattern=re.compile(r'.*\bGesamtbetrag\s+netto\b.*\|\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*EUR\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.95,
        description="label_gesamtbetrag_netto_sevdesk",
    ),
    # STRATO: "| Entspricht der Summe netto | EUR | 26,05 |"
    Rule(
        pattern=re.compile(r'\|\s*Entspricht\s+der\s+Summe\s+netto\s*\|\s*EUR\s*\|\s*([\d]+[.,]\d{2})\s*\|', re.IGNORECASE),
        confidence=0.95,
        description="label_entspricht_summe_netto_strato",
    ),
    # Fastbill: "Zwischensumme\n\n960,00 €" (Standalone-Label, eigene Zeile)
    Rule(
        pattern=re.compile(r'(?<!\w)Zwischensumme\s*\n+\s*' + _AMOUNT, re.IGNORECASE),
        confidence=0.90,
        description="label_zwischensumme_fastbill",
    ),
    # Billomat: "| Zwischensumme netto: | ... | 2.530,00 € |" (Tabelle, letzte Zelle)
    Rule(
        pattern=re.compile(r'.*\bZwischensumme\s+netto\b.*\|\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*€\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.90,
        description="label_zwischensumme_netto_billomat",
    ),
    # Lexoffice: "| Zwischensumme (netto) | ... | 881,00 |" (Tabelle, kein EUR-Suffix)
    Rule(
        pattern=re.compile(r'.*\bZwischensumme\s+\(netto\).*\|\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.90,
        description="label_zwischensumme_netto_lexoffice",
    ),
    # intersport: "Nettosumme | ... | € 69,62" (Tabelle, EUR vor Zahl)
    Rule(
        pattern=re.compile(r'.*\bNettosumme\b.*\|\s*€\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.90,
        description="label_nettosumme_intersport",
    ),
    # fernerofolio: "| Netto | Netto | ... | 138,65 € |" (wiederholte Zellen)
    Rule(
        pattern=re.compile(r'.*\|\s*Netto\s*\|\s*Netto\b.*\|\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*€\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.88,
        description="label_netto_netto_fernerofolio",
    ),
    # billomat_storno Footer: "Netto: 1.200,42 €" (standalone Label außerhalb Tabelle)
    Rule(
        pattern=re.compile(r'\bNetto:\s*([\d]{1,3}(?:\.\d{3})*,\d{2})\s*(?:€|EUR)', re.IGNORECASE),
        confidence=0.85,
        description="label_netto_colon",
    ),
    # word_template: "Summe: €180,00" (Netto als "Summe" bezeichnet, EUR-First)
    Rule(
        pattern=re.compile(r'\bSumme:\s*€\s*([\d]{1,3}(?:\.\d{3})*,\d{2})'),
        confidence=0.85,
        description="label_summe_eur_first_word_template",
    ),
    # Audible: "(ohne USt.) 9.30" — englisches Dezimalformat
    Rule(
        pattern=re.compile(r'\(ohne\s+USt\.\)\s+([\d]+\.\d{2})', re.IGNORECASE),
        confidence=0.80,
        description="label_ohne_ust_audible",
    ),
    # "| USt. Gesamt | ... | 7,85 € | 1,49 € |" — Amazon: vorletzte Zelle = Netto-Basis
    Rule(
        pattern=re.compile(r'.*\bUSt\.?\s+Gesamt\b.*\|\s*([\d]+,\d{2})\s*€\s*\|\s*[\d]+,\d{2}\s*€\s*\|', re.MULTILINE | re.IGNORECASE),
        confidence=0.88,
        description="label_ust_gesamt_netto_amazon",
    ),
    # "Netto: USt 19 % (1.200,42 €)" — billomat_storno: Netto-Basis in Klammern nach MwSt-Label
    Rule(
        pattern=re.compile(r'\bNetto:\s*USt\s+\d+\s*%\s*\(([\d]{1,3}(?:\.\d{3})*,\d{2})\s*€\)', re.IGNORECASE),
        confidence=0.85,
        description="label_netto_ust_klammer_billomat_storno",
    ),
]


# ---------------------------------------------------------------------------
# MWST_SATZ (Prozentsatz als String, z. B. "19,00" oder "19" oder "7")
# Nur den Satz extrahieren — den Betrag haben wir schon in MWST_BETRAG.
# Bei mehreren Sätzen auf einer Rechnung: höchste Confidence gewinnt (ersten Match).
# ---------------------------------------------------------------------------

MWST_SATZ: list[Rule] = [
    # "zzgl. 19,00% MwSt." — Fastbill, intersport
    Rule(
        pattern=re.compile(r'zzgl\.?\s*([\d]+(?:,\d+)?)\s*%\s*MwSt', re.IGNORECASE),
        confidence=0.95,
        description="label_zzgl_pct_mwst",
    ),
    # "Umsatzsteuer (19,00%)" — STRATO
    Rule(
        pattern=re.compile(r'Umsatzsteuer\s*\(([\d]+(?:,\d+)?)\s*%\)', re.IGNORECASE),
        confidence=0.95,
        description="label_umsatzsteuer_klammer_pct",
    ),
    # "Umsatzsteuer 19%" — sevDesk, lexoffice
    Rule(
        pattern=re.compile(r'Umsatzsteuer\s+([\d]+(?:,\d+)?)\s*%', re.IGNORECASE),
        confidence=0.90,
        description="label_umsatzsteuer_pct",
    ),
    # "MwSt (19%)" — word_template
    Rule(
        pattern=re.compile(r'MwSt\s*\(([\d]+(?:,\d+)?)\s*%\)', re.IGNORECASE),
        confidence=0.90,
        description="label_mwst_klammer_pct",
    ),
    # "USt. - Deutschland 19 % inkl." — fernerofolio
    Rule(
        pattern=re.compile(r'USt\.?\s*-\s*Deutschland\s+([\d]+(?:,\d+)?)\s*%', re.IGNORECASE),
        confidence=0.90,
        description="label_ust_deutschland_pct",
    ),
    # "USt 19 %(...)" — billomat
    Rule(
        pattern=re.compile(r'\bUSt\s+([\d]+(?:,\d+)?)\s*%', re.IGNORECASE),
        confidence=0.85,
        description="label_ust_pct_billomat",
    ),
    # "19,0 % MwSt." — bluebrix (Prozent vor Label)
    Rule(
        pattern=re.compile(r'([\d]+(?:,\d+)?)\s*%\s*MwSt', re.IGNORECASE),
        confidence=0.80,
        description="label_pct_mwst_general",
    ),
    # "| 7% | (ohne USt.)" — Audible Zusammenfassungstabelle
    Rule(
        pattern=re.compile(r'\|\s*(\d+)\s*%\s*\|\s*\(?\s*ohne\s+USt\.', re.IGNORECASE),
        confidence=0.75,
        description="label_ust_pct_audible",
    ),
    # "| USt.% | ...\n| 19% | ..." — Amazon: Prozentsatz in Zelle unter USt.%-Spaltenkopf
    # [^%\n]*? non-greedy: verhindert dass "1" aus "19%" vorab konsumiert wird
    Rule(
        pattern=re.compile(r'\bUSt\.%[^\n]*\n[^%\n]*?(\d+(?:,\d+)?)\s*%', re.IGNORECASE),
        confidence=0.75,
        description="label_ust_pct_spalte_amazon",
    ),
]


# ---------------------------------------------------------------------------
# LIEFERANT_NAME (Rechnungssteller / Verkäufer)
# Strategie: Explizite Labels > Verkauft-von > Firmenheadings > Erste Zeile mit Separator
# ---------------------------------------------------------------------------

LIEFERANT_NAME: list[Rule] = [
    # Explizites Label "Lieferant:" — word_template
    Rule(
        pattern=re.compile(r'Lieferant:\s*(.+?)(?=\s+Adresse:|\n|$)', re.IGNORECASE),
        confidence=0.95,
        description="label_lieferant",
    ),
    # "## Verkauft von\n{name}" — Audible, Stripe-Style-Rechnungen
    Rule(
        pattern=re.compile(r'##\s+Verkauft\s+von\s*\n+([^\n]+)', re.IGNORECASE),
        confidence=0.90,
        description="label_verkauft_von_heading",
    ),
    # "Verkauft von {Name}" — Amazon (inline Text, kein Heading)
    Rule(
        pattern=re.compile(r'Verkauft\s+von\s+([A-ZÄÖÜa-zäöüß][^\n|]{5,60}?)(?:[ \t]*\n|[ \t]*$)', re.IGNORECASE),
        confidence=0.85,
        description="label_verkauft_von_inline",
    ),
    # Erste Zeile mit " · " Separator — STRATO, congstar
    # [ \t]+ statt \s+ verhindert zeilenübergreifende Matches
    Rule(
        pattern=re.compile(r'^([^·\n]{5,50}?)[ \t]+·[ \t]+', re.MULTILINE),
        confidence=0.78,
        description="erste_zeile_bullet_separator",
    ),
    # Erste Zeile mit " | " Separator — fastbill, billomat_gutschrift/-storno
    # [ \t]*\| statt \s*\| — Newline vor nächster Tabellenzeile darf nicht überquert werden
    Rule(
        pattern=re.compile(r'^([^|\n]{5,60}?)[ \t]*\|', re.MULTILINE),
        confidence=0.75,
        description="erste_zeile_pipe_separator",
    ),
    # Erste Zeile mit " - " Separator — sevDesk, bluebrix, intersport
    # [^-\n] schließt Bindestriche in Firmenname aus; [ \t]+ statt \s+ keine Zeilenüberquerung
    Rule(
        pattern=re.compile(r'^([A-ZÄÖÜ][^-\n]{4,50}?)[ \t]+-+[ \t]*(?=[A-ZÄÖÜ]|\d)', re.MULTILINE),
        confidence=0.72,
        description="erste_zeile_dash_separator",
    ),
    # Erste Zeile mit ", " Separator — lexoffice
    Rule(
        pattern=re.compile(r'^([A-ZÄÖÜ][^,\n]{5,60}?),[ \t]+(?=[A-ZÄÖÜ]|\d)', re.MULTILINE),
        confidence=0.72,
        description="erste_zeile_comma_separator",
    ),
    # Billomat-Footer: "Grafik- und Werbeagentur Kreativ+ Bergheimer Str. 56"
    # Billomat legt Vendor-Block ans Dokumentende — Zeile endet exakt nach Hausnummer.
    # [^|\n] erlaubt Bindestrich im Firmennamen; \s*$ schlägt fehl wenn PLZ/Stadt folgen.
    Rule(
        pattern=re.compile(
            r'^([A-ZÄÖÜ][^|\n]{5,60}?)\s+[A-ZÄÖÜ][a-zäöüß]+\s+'
            r'(?:Str\.|Straße|Gasse|Weg|Allee|Platz|Ring|Damm|Chaussee)\s+\d+\s*$',
            re.MULTILINE,
        ),
        confidence=0.70,
        description="firma_vor_strassenname_footer",
    ),
    # Firmenname als Heading mit Rechtssuffix — fernerofolio "## Fenerofolio GmbH"
    # Kein IGNORECASE → verhindert "ag" in "Gesamtbetrag" als "AG"-Match
    # [ \t] statt \s → kein Zeilenübergang vor dem Suffix
    # Letzter Fallback — Erst-Zeile-Regeln und Footer-Regel haben Vorrang
    Rule(
        pattern=re.compile(r'##[ \t]+([A-ZÄÖÜ][^#\n]{3,60}?[ \t](?:GmbH|AG|UG|KG|GbR|e\.V\.|Ltd\.?|Inc\.?))\b'),
        confidence=0.82,
        description="label_firma_heading_rechtssuffix",
    ),
]


# ---------------------------------------------------------------------------
# STEUERNUMMER (Finanzamt-Steuernummer, nicht USt-IdNr.)
# Format variiert je Bundesland: "12 345 678 910" / "121/5720/5598"
# ---------------------------------------------------------------------------

STEUERNUMMER: list[Rule] = [
    # "Steuer-Nr.: 12 345 678 910" / "Steuernummer: 78 901 234 567"
    # "STEUER-NR. 98 765 432 109" (sevDesk sidebar, kein Doppelpunkt)
    Rule(
        pattern=re.compile(r'Steuer(?:nummer|[-\s]?Nr\.?)[:.\s]+(\d{2,3}(?:[\s/]\d{3,4}){2,3})', re.IGNORECASE),
        confidence=0.95,
        description="label_steuernummer",
    ),
    # Sidebar-Variante ohne Trennzeichen: "STEUER-NR.\n98 765 432 109"
    Rule(
        pattern=re.compile(r'STEUER[-\s]?NR\.?\s*\n+(\d{2,3}(?:[\s/]\d{3,4}){2,3})'),
        confidence=0.90,
        description="label_steuernummer_sidebar_sevdesk",
    ),
]


# ---------------------------------------------------------------------------
# UST_IDNR (§14 UStG: USt-IdNr. als Alternative zur Steuernummer)
# Format: DE gefolgt von genau 9 Ziffern (ISO 6523)
# ---------------------------------------------------------------------------

UST_IDNR: list[Rule] = [
    # "USt-IdNr.: DE123456789" / "USt-Id.Nr.: DE 283508818" — Standard + Intersport-Variante
    # DE-Zahl kann Leerzeichen enthalten (z.B. "DE 211 045 709") — wird in _clean_value normalisiert
    Rule(
        pattern=re.compile(r'USt\.?-?Id\.?(?:Nr\.?|entifikationsnummer)?[:\s]+(DE[\s\d]{9,13})', re.IGNORECASE),
        confidence=0.95,
        description="label_ust_idnr",
    ),
    # "UST-ID-NR.\nDE 211 045 709" — STRATO Footer (Großbuchstaben, Zeilenumbruch)
    Rule(
        pattern=re.compile(r'UST-ID-NR\.?\s+(DE[\s\d]{9,13})', re.IGNORECASE),
        confidence=0.93,
        description="label_ust_id_nr_strato",
    ),
    # "Umsatzsteuer-ID: DE 789 012 345" — Billomat Footer
    Rule(
        pattern=re.compile(r'Umsatzsteuer-ID[:\s]+(DE[\s\d]{9,13})', re.IGNORECASE),
        confidence=0.92,
        description="label_umsatzsteuer_id_billomat",
    ),
    # "Steuer-Nr. DE123456789" — wenn DE-Präfix direkt auf Steuer-Label folgt
    Rule(
        pattern=re.compile(r'(?:Steuer|USt)[-\s]?(?:Nr\.?|Nummer)[:\s]+(DE[\s\d]{9,13})', re.IGNORECASE),
        confidence=0.90,
        description="label_ust_nr_mit_de_praefix",
    ),
    # "VAT-ID: DE123456789" — bei internationalen Lieferanten
    Rule(
        pattern=re.compile(r'VAT[-\s]?(?:ID|Nr\.?)[:\s]+(DE[\s\d]{9,13})', re.IGNORECASE),
        confidence=0.85,
        description="label_vat_id",
    ),
    # Rohformat: DE gefolgt von genau 9 Ziffern ohne Leerzeichen (Fallback ohne Label)
    Rule(
        pattern=re.compile(r'\b(DE\d{9})\b'),
        confidence=0.70,
        description="format_de_9ziffern_fallback",
    ),
]


# ---------------------------------------------------------------------------
# LEISTUNGSDATUM (Zeitpunkt der Lieferung/Leistung — §14 Abs. 4 Nr. 6 UStG)
# DATEV bevorzugt dieses Datum als Buchungsdatum gegenüber dem Rechnungsdatum.
# Wenn nicht gefunden: Fallback auf `datum` im DATEV-Export (dokumentiert).
# ---------------------------------------------------------------------------

LEISTUNGSDATUM: list[Rule] = [
    # "Leistungsdatum: 15.04.2026"
    Rule(
        pattern=re.compile(r'Leistungsdatum[:\s]+(\d{2}\.\d{2}\.\d{4})', re.IGNORECASE),
        confidence=0.95,
        description="label_leistungsdatum",
    ),
    # "Lieferdatum: 15.04.2026" — einfaches Label direkt vor dem Datum
    Rule(
        pattern=re.compile(r'Lieferdatum[:\s]+(\d{2}\.\d{2}\.\d{4})', re.IGNORECASE),
        confidence=0.90,
        description="label_lieferdatum",
    ),
    # Lexoffice Sidebar: "Datum:\nLieferdatum:\n{nicht-Datum-Zeilen}\n{datum}\n{lieferdatum}"
    # Docling rendert 2-Spalten-Tabellen so: erst alle Labels, dann alle Werte.
    # Wir überspringen nicht-Datum-Zeilen (Rechnungsnr, Kundennr), dann erstes Datum (=Rechnungsdatum),
    # dann zweites Datum (=Lieferdatum) als group(1).
    Rule(
        pattern=re.compile(
            r'Datum:\s*\n+Lieferdatum:\s*\n+'
            r'(?:(?!\d{2}\.\d{2}\.\d{4})[^\n]*\n+)+'
            r'\d{2}\.\d{2}\.\d{4}\s*\n+'
            r'(\d{2}\.\d{2}\.\d{4})',
        ),
        confidence=0.88,
        description="label_lieferdatum_lexoffice_sidebar",
    ),
    # SevDesk Sidebar: "Gutschrift-Nr. Datum Leistungszeitraum\n{nr}\n{datum}\n{dd.mm.yyyy - dd.mm.yyyy}"
    # Überspringt Rechnungsnr-Wert und Datum-Wert, landet dann auf dem Zeitraum-Startdatum.
    Rule(
        pattern=re.compile(
            r'Leistungszeitraum\s*\n+'
            r'\S+\s*\n+'
            r'\d{2}\.\d{2}\.\d{4}\s*\n+'
            r'(\d{2}\.\d{2}\.\d{4})\s*-',
        ),
        confidence=0.85,
        description="label_leistungszeitraum_sevdesk_sidebar",
    ),
    # "Leistungszeitraum: 01.03.2026 – 31.03.2026" → erstes Datum (Beginn des Zeitraums)
    Rule(
        pattern=re.compile(r'Leistungszeitraum[:\s]+(\d{2}\.\d{2}\.\d{4})', re.IGNORECASE),
        confidence=0.80,
        description="label_leistungszeitraum_start",
    ),
    # congstar: "für deine genutzten Leistungen vom" + (einige Zeilen weiter) Datumbereich
    # Docling trennt Labels und Werte im 2-Spalten-Layout — tempered greedy überspringt
    # einzeln stehende Daten (Rechnungsdatum) und landet am ersten "DD.MM.YYYY -"-Muster.
    Rule(
        pattern=re.compile(
            r'für (?:deine|Ihre) (?:genutzten )?Leistungen vom'
            r'(?:(?!\d{2}\.\d{2}\.\d{4}\s*[-–])[\s\S])*?'
            r'(\d{2}\.\d{2}\.\d{4})\s*[-–]',
            re.IGNORECASE,
        ),
        confidence=0.82,
        description="label_leistungen_vom_congstar",
    ),
    # Amazon Audible: "Bestelldatum\n\n09 Apr 2026" — englisches Kurzdatum nach Label
    Rule(
        pattern=re.compile(
            r'Bestelldatum\s+'
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
            re.IGNORECASE,
        ),
        confidence=0.72,
        description="label_bestelldatum_audible",
    ),
    # Strato: "vom 13.12.2025 bis 12.01.2026" eingebettet in Artikelbeschreibung
    # Kein explizites Leistungszeitraum-Label — Confidence niedrig.
    Rule(
        pattern=re.compile(r'\bvom\s+(\d{2}\.\d{2}\.\d{4})\s+bis\s+\d{2}\.\d{2}\.\d{4}', re.IGNORECASE),
        confidence=0.60,
        description="label_vom_bis_strato",
    ),
    # Letzter Fallback: beliebiger Datumbereich DD.MM.YYYY - DD.MM.YYYY im Dokument
    # Trifft z. B. fernerofolio (Laufzeit in Tabellenzeile: "25.12.2025 - 25.12.2026").
    Rule(
        pattern=re.compile(r'(\d{2}\.\d{2}\.\d{4})\s*[-–]\s*\d{2}\.\d{2}\.\d{4}'),
        confidence=0.55,
        description="datum_bereich_start_fallback",
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
    "dokumenttyp":     DOKUMENTTYP,
    "netto_betrag":    NETTO_BETRAG,
    "mwst_satz":       MWST_SATZ,
    "lieferant_name":  LIEFERANT_NAME,
    "steuernummer":    STEUERNUMMER,
    "ust_idnr":        UST_IDNR,
    "leistungsdatum":  LEISTUNGSDATUM,
}
