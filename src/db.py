"""db.py — PostgreSQL-Verbindung.

Liest Credentials aus Umgebungsvariablen (identisch mit docker-compose.yml).
Nutze get_conn() als Context-Manager: commit bei Erfolg, rollback bei Fehler.

Beispiel:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1")
"""

import os
from contextlib import contextmanager

import psycopg2

_DSN = (
    "postgresql://{user}:{password}@{host}:{port}/{dbname}".format(
        user=os.getenv("POSTGRES_USER", "invoice_ai"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_HOST_PORT", "55432"),
        dbname=os.getenv("POSTGRES_DB", "invoice_ai"),
    )
)


@contextmanager
def get_conn():
    conn = psycopg2.connect(_DSN)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
