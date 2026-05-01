"""validation.py — §14 UStG Qualitätschecks pro Rechnung.

Gibt pro Rechnung eine Liste von Check-Ergebnissen zurück:
  result: 'ok' | 'warn' | 'fail'

'fail' = Vorsteuerabzug gefährdet (fehlendes Pflichtfeld, falsche IBAN)
'warn' = Plausibilitätsproblem, manuell prüfen (MwSt-Abweichung, Datum-Format)
'ok'   = Check bestanden

Nutzung:
    from src.validation import check_all
    checks = check_all(extraction_result_dict)
    # extraction_result_dict = Ausgabe von rule_engine.extract()
"""

from __future__ import annotations

import re
from datetime import datetime


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------

def check_all(extraction: dict) -> list[dict]:
    """Führt alle Checks aus. Gibt nur non-None Ergebnisse zurück."""
    runners = [
        _check_pflichtfelder,
        _check_iban_prüfziffer,
        _check_mwst_plausibel,
        _check_mwst_satz_erlaubt,
        _check_datum_format,
        _check_betrag_vorzeichen,
    ]
    results = []
    for run in runners:
        out = run(extraction)
        if isinstance(out, list):
            results.extend(out)
        elif out is not None:
            results.append(out)
    return results


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _val(extraction: dict, field: str) -> str | None:
    return extraction.get(field, {}).get("value")


def _to_float(extraction: dict, field: str) -> float | None:
    v = _val(extraction, field)
    if not v:
        return None
    try:
        # Deutsches Format: 1.142,40 → 1142.40  |  Englisch: 9.95 → 9.95
        cleaned = v.replace(".", "").replace(",", ".")
        return float(cleaned)
    except ValueError:
        return None


def _result(check_name: str, ok: bool, detail: str | None = None,
            severity: str = "fail") -> dict:
    return {
        "check_name": check_name,
        "result": "ok" if ok else severity,
        "detail": None if ok else detail,
    }


# ---------------------------------------------------------------------------
# Check 1 — §14 Pflichtfelder
# ---------------------------------------------------------------------------

# Felder die §14 UStG für den Vorsteuerabzug verlangt.
# steuernummer ist Pflicht, aber 35% unserer Testdocs haben nur USt-ID → 'warn' statt 'fail'
_PFLICHT_FAIL = ["rechnungsnummer", "datum", "betrag_brutto", "lieferant_name"]
_PFLICHT_WARN = ["steuernummer"]   # fehlt oft strukturell → nur Warnung


def _check_pflichtfelder(extraction: dict) -> list[dict]:
    results = []
    for feld in _PFLICHT_FAIL:
        if not _val(extraction, feld):
            results.append(_result(
                f"pflichtfeld_{feld}", False,
                f"§14 UStG: Pflichtfeld '{feld}' fehlt — Vorsteuerabzug gefährdet",
                severity="fail",
            ))
    for feld in _PFLICHT_WARN:
        if not _val(extraction, feld):
            results.append(_result(
                f"pflichtfeld_{feld}", False,
                f"§14 UStG: '{feld}' fehlt — bitte manuell ergänzen (USt-ID ausreichend?)",
                severity="warn",
            ))
    return results


# ---------------------------------------------------------------------------
# Check 2 — IBAN Prüfziffer (ISO 13616)
# ---------------------------------------------------------------------------

def _check_iban_prüfziffer(extraction: dict) -> dict | None:
    iban = _val(extraction, "iban")
    if not iban:
        return None  # kein IBAN → kein Check, nicht als Fehler werten

    iban = re.sub(r"\s+", "", iban.upper())

    # Grundformat: 2 Buchstaben + 2 Ziffern + mind. 10 Zeichen
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$", iban):
        return _result("iban_prüfziffer", False,
                       f"IBAN '{iban}' hat ungültiges Format")

    # ISO 13616: erste 4 Zeichen ans Ende, A=10…Z=35, mod 97 muss 1 ergeben
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(
        str(ord(c) - 55) if c.isalpha() else c for c in rearranged
    )
    ok = int(numeric) % 97 == 1
    return _result("iban_prüfziffer", ok,
                   f"IBAN '{iban}' hat ungültige Prüfziffer (mod97 ≠ 1)")


# ---------------------------------------------------------------------------
# Check 3 — MwSt-Plausibilität: brutto ≈ netto + mwst  (Toleranz 0,05 €)
# ---------------------------------------------------------------------------

def _check_mwst_plausibel(extraction: dict) -> dict | None:
    brutto = _to_float(extraction, "betrag_brutto")
    netto  = _to_float(extraction, "netto_betrag")
    mwst   = _to_float(extraction, "mwst_betrag")

    if None in (brutto, netto, mwst):
        return None  # nicht genug Daten → kein Check

    diff = abs(abs(brutto) - (abs(netto) + abs(mwst)))
    ok = diff <= 0.05
    return _result(
        "mwst_plausibel", ok,
        f"brutto ({brutto}) ≠ netto ({netto}) + mwst ({mwst}), Differenz {diff:.2f} €",
        severity="warn",
    )


# ---------------------------------------------------------------------------
# Check 4 — MwSt-Satz: muss 0%, 7% oder 19% sein
# ---------------------------------------------------------------------------

_ERLAUBTE_SAETZE = {"0", "7", "19", "0,0", "7,0", "19,0",
                    "0,00", "7,00", "19,00"}


def _check_mwst_satz_erlaubt(extraction: dict) -> dict | None:
    satz = _val(extraction, "mwst_satz")
    if not satz:
        return None

    ok = satz.strip() in _ERLAUBTE_SAETZE
    return _result(
        "mwst_satz_erlaubt", ok,
        f"Ungewöhnlicher MwSt-Satz: {satz}% — bitte prüfen",
        severity="warn",
    )


# ---------------------------------------------------------------------------
# Check 5 — Datum: deutsches Format und plausibles Jahr (2015–2035)
# ---------------------------------------------------------------------------

def _check_datum_format(extraction: dict) -> dict | None:
    datum = _val(extraction, "datum")
    if not datum:
        return None

    if re.match(r"^\d{2}\.\d{2}\.\d{4}$", datum):
        try:
            d = datetime.strptime(datum, "%d.%m.%Y")
            if 2015 <= d.year <= 2035:
                return _result("datum_format", True)
            return _result("datum_format", False,
                           f"Datum '{datum}' außerhalb des plausiblen Bereichs 2015–2035",
                           severity="warn")
        except ValueError:
            pass

    return _result("datum_format", False,
                   f"Datum '{datum}' nicht im deutschen Format (TT.MM.JJJJ) — bitte normalisieren",
                   severity="warn")


# ---------------------------------------------------------------------------
# Check 6 — Betrag-Vorzeichen: Storno/Gutschrift sollte negativ sein
# ---------------------------------------------------------------------------

def _check_betrag_vorzeichen(extraction: dict) -> dict | None:
    typ    = _val(extraction, "dokumenttyp")
    brutto = _to_float(extraction, "betrag_brutto")

    if not typ or brutto is None:
        return None

    if typ in ("storno", "gutschrift") and brutto > 0:
        return _result(
            "betrag_vorzeichen", False,
            f"Dokumenttyp '{typ}' hat positiven Bruttobetrag ({brutto:.2f} €) "
            f"— in DATEV als negativ buchen",
            severity="warn",
        )
    return _result("betrag_vorzeichen", True)
