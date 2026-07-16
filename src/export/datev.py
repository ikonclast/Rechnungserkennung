"""datev.py — DATEV CSV Export (Phase 1: Semikolon-CSV, UTF-8).

Nur Rechnungen mit mindestens einem confirmations-Eintrag werden exportiert.
Buchungsdatum: leistungsdatum wenn vorhanden, sonst datum.
Storno/Gutschrift: Betrag negativ.

Steuercode-Mapping (Phase 1):
  19% → 9 | 7% → 2 | 0% → 40 | (unbekannt) → 0
"""

import csv
import io
from datetime import date

from src.db import get_conn

_STEUERCODE: dict[str, int] = {"19": 9, "19.0": 9, "7": 2, "7.0": 2, "0": 40, "0.0": 40}
_STORNO_TYPEN = {"storno", "gutschrift"}

_QUERY = """
SELECT
    d.id                                             AS doc_id,
    COALESCE(ee.eff_leistungsdatum, ee.eff_datum)    AS buchungsdatum,
    ee.eff_rechnungsnummer                           AS belegnummer,
    ee.eff_betrag_brutto                             AS betrag_brutto,
    ee.eff_netto_betrag                              AS betrag_netto,
    ee.eff_mwst_satz                                 AS mwst_satz,
    ee.eff_lieferant_name                            AS lieferant,
    ee.dokumenttyp                                   AS dokumenttyp
FROM documents d
JOIN v_effective_extractions ee ON ee.document_id = d.id
WHERE EXISTS (
    SELECT 1 FROM confirmations c WHERE c.extraction_id = ee.id
)
{date_filter}
ORDER BY buchungsdatum NULLS LAST, d.id
"""


def _parse_float(val: str | None) -> float | None:
    if not val:
        return None
    try:
        return float(val.replace(",", ".").replace("€", "").strip())
    except ValueError:
        return None


def _steuercode(mwst_satz: str | None) -> int:
    if not mwst_satz:
        return 0
    key = mwst_satz.strip().rstrip("%").strip()
    return _STEUERCODE.get(key, 0)


def generate_csv(date_from: date | None = None, date_to: date | None = None) -> bytes:
    """Erstellt DATEV CSV als UTF-8-Bytes. Nur confirmed Rechnungen."""
    params: list = []
    filter_clauses: list[str] = []

    if date_from:
        filter_clauses.append("AND COALESCE(ee.eff_leistungsdatum, ee.eff_datum) >= %s")
        params.append(str(date_from))
    if date_to:
        filter_clauses.append("AND COALESCE(ee.eff_leistungsdatum, ee.eff_datum) <= %s")
        params.append(str(date_to))

    query = _QUERY.format(date_filter="\n".join(filter_clauses))

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description]

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    writer.writerow(["Buchungsdatum", "Belegnummer", "Betrag_Netto", "Steuercode",
                     "Lieferant", "Buchungstext", "Exportiert_am"])

    export_ts = date.today().isoformat()

    for row in rows:
        r = dict(zip(col_names, row))

        netto = _parse_float(r.get("betrag_netto")) or _parse_float(r.get("betrag_brutto"))
        if netto is None:
            netto = 0.0

        if r.get("dokumenttyp", "").lower() in _STORNO_TYPEN:
            netto = -abs(netto)

        steuercode = _steuercode(r.get("mwst_satz"))
        lieferant = r.get("lieferant") or ""
        buchungstext = f"{r.get('dokumenttyp', '')} {lieferant}".strip()

        writer.writerow([
            r.get("buchungsdatum") or "",
            r.get("belegnummer") or "",
            f"{netto:.2f}".replace(".", ","),
            steuercode,
            lieferant,
            buchungstext,
            export_ts,
        ])

    return buf.getvalue().encode("utf-8-sig")  # BOM für Excel-Kompatibilität
