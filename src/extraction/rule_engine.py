"""rule_engine.py

Extrahiert strukturierte Felder aus normalisiertem Docling-Markdown.
Gibt pro Feld: Wert, Confidence-Score und die angeschlagene Regel zurück.

Nutzung:
    from src.extraction.rule_engine import extract, extract_from_file
    result = extract(text)
    result["rechnungsnummer"]["value"]      → "EM-2026-3"
    result["rechnungsnummer"]["confidence"] → 0.85
    result["rechnungsnummer"]["rule"]       → "label_rechnung_nr_fastbill"
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

from .field_definitions import ALL_FIELDS, Rule


class FieldResult(TypedDict):
    value: str | None
    confidence: float
    rule: str | None


ExtractionResult = dict[str, FieldResult]


def _clean_iban(value: str) -> str:
    # IBAN-Werte können Leerzeichen enthalten ("DE89 6722 0070...")
    return re.sub(r'\s+', '', value) if value else value


def _clean_value(field_name: str, value: str) -> str:
    value = value.strip()
    if field_name == "iban":
        import re
        return re.sub(r'\s+', '', value)
    return value


def _is_plausible(field_name: str, value: str) -> bool:
    if field_name == "rechnungsnummer":
        # Echte Rechnungsnummern enthalten immer mindestens eine Ziffer.
        # Schließt Wörter wie "Seite", "auf", "Nummer" aus.
        return bool(re.search(r'\d', value))
    return True


def _match_field(field_name: str, text: str, rules: list[Rule]) -> FieldResult:
    for rule in rules:
        m = rule.pattern.search(text)
        if m:
            if rule.fixed_value is not None:
                value = rule.fixed_value
            else:
                value = _clean_value(field_name, m.group(1))
            if value and _is_plausible(field_name, value):
                return {"value": value, "confidence": rule.confidence, "rule": rule.description}
    return {"value": None, "confidence": 0.0, "rule": None}


def _detect_dokumenttyp(text: str, brutto_result: FieldResult) -> FieldResult:
    """Dokumenttyp mit Cross-Field-Logik: erst Regex-Regeln, dann brutto-basierte KBR-Erkennung."""
    result = _match_field("dokumenttyp", text, ALL_FIELDS["dokumenttyp"])
    if result["value"] is not None:
        return result

    # Kleinbetragsrechnung §33 UStDV: Brutto ≤ 250 EUR
    brutto_str = brutto_result.get("value")
    if brutto_str:
        try:
            brutto_val = float(brutto_str.replace(".", "").replace(",", "."))
            if 0 < brutto_val <= 250.0:
                return {"value": "kleinbetragsrechnung", "confidence": 0.80, "rule": "brutto_leq_250_kbr"}
        except (ValueError, AttributeError):
            pass

    return {"value": "rechnung", "confidence": 0.70, "rule": "default_rechnung"}


def extract(text: str) -> ExtractionResult:
    """Extrahiert alle Felder aus einem normalisierten Markdown-Text."""
    result: ExtractionResult = {
        field: _match_field(field, text, rules)
        for field, rules in ALL_FIELDS.items()
        if field != "dokumenttyp"
    }
    result["dokumenttyp"] = _detect_dokumenttyp(text, result.get("betrag_brutto", {}))
    return result


def extract_from_file(path: Path) -> ExtractionResult:
    """Liest eine .md-Datei und extrahiert alle Felder."""
    return extract(path.read_text(encoding="utf-8"))
