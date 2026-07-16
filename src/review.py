"""review.py — Confirmations und Feldkorrekturen.

GoBD: append-only. Kein UPDATE auf extractions.
confirmed_by / corrected_by kommen als Name-String aus dem UI-Cookie.
"""

from src.db import get_conn


def confirm_extraction(extraction_id: int, confirmed_by: str, note: str | None = None) -> int:
    """Legt einen confirmations-Eintrag an. Gibt die neue ID zurück."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO confirmations (extraction_id, confirmed_by, note) VALUES (%s, %s, %s) RETURNING id",
            (extraction_id, confirmed_by, note),
        )
        return cur.fetchone()[0]


def save_correction(
    extraction_id: int,
    field_name: str,
    value: str,
    corrected_by: str,
    note: str | None = None,
) -> int:
    """Speichert eine manuelle Feldkorrektur (GoBD: append-only). Gibt die neue ID zurück."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO field_corrections
               (extraction_id, field_name, corrected_value, corrected_by, note)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (extraction_id, field_name, value, corrected_by, note),
        )
        return cur.fetchone()[0]


def is_confirmed(extraction_id: int) -> bool:
    """Prüft ob eine Extraktion bereits mindestens einmal bestätigt wurde."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM confirmations WHERE extraction_id = %s LIMIT 1",
            (extraction_id,),
        )
        return cur.fetchone() is not None
