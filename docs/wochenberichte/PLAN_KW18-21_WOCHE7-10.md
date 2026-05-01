# Plan — KW18–21 / Woche 7–10
**Erstellt:** 01.05.2026 | **Zeitraum:** 04.05.–29.05.2026
**Voraussetzung:** Woche 5–6 abgeschlossen ✅ (alle 10 Felder, Rule Engine produktionsreif)

---

## Überblick

| Woche | Thema | Ziel |
|---|---|---|
| **7–8** | Datenbankschema + Ingestion | PDF → DB, End-to-End Pipeline steht |
| **9–10** | Validierung + §14-Checks | Ungültige Rechnungen werden erkannt + markiert |

---

---

# WOCHE 7–8: Datenbankschema + Ingestion Service

**Zeitaufwand:** ~12–15h gesamt | **KW:** 19–20

## Hintergrundfrage: Warum append-only?

GoBD §14b schreibt 10 Jahre Aufbewahrungspflicht vor — und verbietet die nachträgliche
Veränderung von Buchhaltungsbelegen. Das bedeutet:

- **Kein `UPDATE`** auf Rechnungsdaten nach dem Speichern
- **Kein `DELETE`** — nie
- **Korrekturen** = neuer Datensatz, nicht Überschreiben des alten
- **Audit-Log** = PostgreSQL-Trigger schreibt automatisch mit, nicht manuell

Das Gegenteil (normale relationale DB mit UPDATE/DELETE) wäre ein GoBD-Verstoß und
würde den Vorsteuerabzug des Kunden gefährden.

---

## Schritt 1 — Dateistruktur anlegen (15 min)

```bash
mkdir -p db src
touch db/schema.sql src/storage.py src/db.py
```

Danach existiert:
```
db/
  schema.sql          ← alle CREATE TABLE + TRIGGER Statements
src/
  storage.py          ← MinIO-Wrapper (upload, download, exists)
  db.py               ← PostgreSQL-Verbindung + Hilfsfunktionen
  extraction/         ← bereits vorhanden (rule_engine, field_definitions)
scripts/
  ingest_invoice.py   ← Haupt-Ingestion-Script (neu)
```

---

## Schritt 2 — Datenbankschema schreiben (`db/schema.sql`) (2–3h)

### 2a. Tabellen

```sql
-- Datenbank erstellen (einmalig):
-- CREATE DATABASE invoices;

-- documents: jede Rechnung genau einmal
-- sha256 UNIQUE verhindert Duplikate auf DB-Ebene
CREATE TABLE documents (
    id           BIGSERIAL PRIMARY KEY,
    sha256       CHAR(64)     NOT NULL UNIQUE,
    filename     TEXT         NOT NULL,
    minio_path   TEXT         NOT NULL,
    status       TEXT         NOT NULL DEFAULT 'uploaded',
    retain_until DATE         NOT NULL,   -- heute + 10 Jahre (GoBD)
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- extractions: Ergebnis der Rule Engine pro Verarbeitungslauf
-- Alle Felder als TEXT — Normalisierung kommt in Woche 9
CREATE TABLE extractions (
    id                    BIGSERIAL    PRIMARY KEY,
    document_id           BIGINT       NOT NULL REFERENCES documents(id),
    engine_version        TEXT         NOT NULL,   -- z.B. "rule_engine_v1"
    rechnungsnummer       TEXT,         rechnungsnummer_conf  REAL,
    datum                 TEXT,         datum_conf            REAL,
    betrag_brutto         TEXT,         betrag_brutto_conf    REAL,
    mwst_betrag           TEXT,         mwst_betrag_conf      REAL,
    netto_betrag          TEXT,         netto_betrag_conf     REAL,
    mwst_satz             TEXT,         mwst_satz_conf        REAL,
    dokumenttyp           TEXT,         dokumenttyp_conf      REAL,
    lieferant_name        TEXT,         lieferant_name_conf   REAL,
    steuernummer          TEXT,         steuernummer_conf     REAL,
    iban                  TEXT,         iban_conf             REAL,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- validations: Ergebnis der §14-Checks (Woche 9)
CREATE TABLE validations (
    id              BIGSERIAL    PRIMARY KEY,
    extraction_id   BIGINT       NOT NULL REFERENCES extractions(id),
    check_name      TEXT         NOT NULL,   -- z.B. "iban_checksum", "mwst_plausibel"
    result          TEXT         NOT NULL,   -- 'ok' | 'warn' | 'fail'
    detail          TEXT,                    -- Beschreibung des Fehlers
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- confirmations: menschliche Bestätigung (Human-in-the-Loop, Woche 11+)
CREATE TABLE confirmations (
    id              BIGSERIAL    PRIMARY KEY,
    extraction_id   BIGINT       NOT NULL REFERENCES extractions(id),
    confirmed_by    TEXT         NOT NULL,   -- Benutzername
    confirmed_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    note            TEXT                     -- optionaler Kommentar
);

-- audit_log: automatisch befüllt per Trigger
CREATE TABLE audit_log (
    id          BIGSERIAL    PRIMARY KEY,
    table_name  TEXT         NOT NULL,
    row_id      BIGINT       NOT NULL,
    action      TEXT         NOT NULL,   -- 'INSERT' (UPDATE/DELETE verboten)
    payload     JSONB        NOT NULL,
    logged_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

### 2b. Trigger (Audit-Log automatisch)

```sql
-- Funktion: bei jedem INSERT in documents/extractions → audit_log Eintrag
CREATE OR REPLACE FUNCTION fn_audit_insert()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO audit_log(table_name, row_id, action, payload)
    VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW)::jsonb);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_audit_documents
    AFTER INSERT ON documents
    FOR EACH ROW EXECUTE FUNCTION fn_audit_insert();

CREATE TRIGGER trg_audit_extractions
    AFTER INSERT ON extractions
    FOR EACH ROW EXECUTE FUNCTION fn_audit_insert();

-- Schutz: UPDATE/DELETE auf documents verbieten
CREATE OR REPLACE FUNCTION fn_no_update_delete()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'UPDATE/DELETE auf % verboten (GoBD append-only)', TG_TABLE_NAME;
END;
$$;

CREATE TRIGGER trg_no_update_documents
    BEFORE UPDATE OR DELETE ON documents
    FOR EACH ROW EXECUTE FUNCTION fn_no_update_delete();

CREATE TRIGGER trg_no_update_extractions
    BEFORE UPDATE OR DELETE ON extractions
    FOR EACH ROW EXECUTE FUNCTION fn_no_update_delete();
```

### 2c. Schema einspielen

```bash
docker compose up -d
psql -h localhost -U postgres -c "CREATE DATABASE invoices;"
psql -h localhost -U postgres -d invoices -f db/schema.sql
psql -h localhost -U postgres -d invoices -c "\dt"    # alle Tabellen anzeigen
```

**Erwartete Ausgabe:**
```
 Schema |     Name      | Type  |  Owner
--------+---------------+-------+----------
 public | audit_log     | table | postgres
 public | confirmations | table | postgres
 public | documents     | table | postgres
 public | extractions   | table | postgres
 public | validations   | table | postgres
```

---

## Schritt 3 — PostgreSQL-Verbindung (`src/db.py`) (30 min)

```python
# src/db.py
import os
import psycopg2
from contextlib import contextmanager

DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/invoices")

@contextmanager
def get_conn():
    conn = psycopg2.connect(DSN)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

---

## Schritt 4 — MinIO-Wrapper (`src/storage.py`) (1h)

```python
# src/storage.py
import os
from minio import Minio

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS   = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET   = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET         = "invoices"

def _client():
    return Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS,
                 secret_key=MINIO_SECRET, secure=False)

def ensure_bucket():
    c = _client()
    if not c.bucket_exists(BUCKET):
        c.make_bucket(BUCKET)

def upload(local_path: str, object_name: str) -> str:
    ensure_bucket()
    _client().fput_object(BUCKET, object_name, local_path)
    return f"{BUCKET}/{object_name}"

def exists(object_name: str) -> bool:
    try:
        _client().stat_object(BUCKET, object_name)
        return True
    except Exception:
        return False
```

---

## Schritt 5 — Ingestion Script (`scripts/ingest_invoice.py`) (2–3h)

```
Ablauf (jede Rechnung):
  1. SHA-256 berechnen
  2. Doppelt? → abbrechen mit Hinweis
  3. MinIO Upload → Pfad merken
  4. DB INSERT documents (in Transaktion)
  5. Docling → normalize → Rule Engine
  6. DB INSERT extractions
  7. Fertig — Ergebnis ausgeben
```

```python
# scripts/ingest_invoice.py
import hashlib, sys
from datetime import date, timedelta
from pathlib import Path

# Imports aus dem Projekt
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import storage, db
from src.extraction.rule_engine import extract_from_file
# ... normalize_docling_output import

def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def ingest(pdf_path: Path):
    sha = sha256_of_file(pdf_path)
    print(f"SHA-256: {sha[:16]}...")

    with db.get_conn() as conn:
        cur = conn.cursor()

        # Duplikat-Check
        cur.execute("SELECT id, filename FROM documents WHERE sha256 = %s", (sha,))
        existing = cur.fetchone()
        if existing:
            print(f"Duplikat: {pdf_path.name} ist identisch mit Dokument #{existing[0]} ({existing[1]})")
            return

        # MinIO Upload
        object_name = f"{sha[:8]}/{pdf_path.name}"
        minio_path = storage.upload(str(pdf_path), object_name)
        print(f"MinIO: {minio_path}")

        # documents INSERT
        retain_until = date.today() + timedelta(days=3650)  # 10 Jahre
        cur.execute(
            "INSERT INTO documents (sha256, filename, minio_path, retain_until) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (sha, pdf_path.name, minio_path, retain_until)
        )
        doc_id = cur.fetchone()[0]
        print(f"documents #{doc_id} angelegt")

        # Docling + Normalisierung + Rule Engine
        # (hier Docling-Aufruf einbauen oder auf bereits normalisierte Datei verweisen)
        md_path = Path("output/normalized/realtestdata_v2") / (pdf_path.stem + ".md")
        result = extract_from_file(md_path)

        # extractions INSERT
        cur.execute("""
            INSERT INTO extractions (
                document_id, engine_version,
                rechnungsnummer, rechnungsnummer_conf,
                datum, datum_conf,
                betrag_brutto, betrag_brutto_conf,
                mwst_betrag, mwst_betrag_conf,
                netto_betrag, netto_betrag_conf,
                mwst_satz, mwst_satz_conf,
                dokumenttyp, dokumenttyp_conf,
                lieferant_name, lieferant_name_conf,
                steuernummer, steuernummer_conf,
                iban, iban_conf
            ) VALUES (
                %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """, (
            doc_id, "rule_engine_v1",
            result["rechnungsnummer"]["value"], result["rechnungsnummer"]["confidence"],
            result["datum"]["value"],           result["datum"]["confidence"],
            result["betrag_brutto"]["value"],   result["betrag_brutto"]["confidence"],
            result["mwst_betrag"]["value"],     result["mwst_betrag"]["confidence"],
            result["netto_betrag"]["value"],    result["netto_betrag"]["confidence"],
            result["mwst_satz"]["value"],       result["mwst_satz"]["confidence"],
            result["dokumenttyp"]["value"],     result["dokumenttyp"]["confidence"],
            result["lieferant_name"]["value"],  result["lieferant_name"]["confidence"],
            result["steuernummer"]["value"],    result["steuernummer"]["confidence"],
            result["iban"]["value"],            result["iban"]["confidence"],
        ))
        extr_id = cur.fetchone()[0]
        print(f"extractions #{extr_id} angelegt")
        print(f"  Rechnungsnr.: {result['rechnungsnummer']['value']}")
        print(f"  Brutto:       {result['betrag_brutto']['value']} €")
        print(f"  Typ:          {result['dokumenttyp']['value']}")

if __name__ == "__main__":
    ingest(Path(sys.argv[1]))
```

---

## Schritt 6 — End-to-End testen (1h)

```bash
# Abhängigkeiten installieren
.venv/bin/pip install psycopg2-binary minio

# Einzelrechnung testen
.venv/bin/python scripts/ingest_invoice.py \
    samples/realtestdata/fastbill_standard_001.pdf

# Duplikat testen (selbe Datei nochmal) → muss "Duplikat" sagen
.venv/bin/python scripts/ingest_invoice.py \
    samples/realtestdata/fastbill_standard_001.pdf

# Alle 26 Rechnungen ingesten
for f in samples/realtestdata/*.pdf; do
    .venv/bin/python scripts/ingest_invoice.py "$f"
done

# Ergebnis prüfen
psql -h localhost -U postgres -d invoices -c "
SELECT d.filename, e.rechnungsnummer, e.betrag_brutto, e.dokumenttyp
FROM documents d JOIN extractions e ON e.document_id = d.id
ORDER BY d.created_at;"

# Audit-Log prüfen — muss automatisch befüllt sein
psql -h localhost -U postgres -d invoices -c "
SELECT table_name, row_id, action, logged_at FROM audit_log LIMIT 10;"

# GoBD-Schutz testen — muss EXCEPTION werfen
psql -h localhost -U postgres -d invoices -c "
UPDATE documents SET status = 'geaendert' WHERE id = 1;"
```

---

## Schritt 7 — Commit (15 min)

```bash
git add db/schema.sql src/db.py src/storage.py scripts/ingest_invoice.py
git commit -m "feat: Woche 7-8 — Datenbankschema (append-only) + Ingestion Service"
```

**Woche 7–8 Ergebnis:** 26 Rechnungen in DB, Audit-Log läuft, Duplikat-Schutz funktioniert.

---
---

# WOCHE 9–10: Validierung + §14 UStG Checks

**Zeitaufwand:** ~10–12h gesamt | **KW:** 21

## Was validiert wird

§14 UStG schreibt Pflichtangaben vor. Fehlt eins → Vorsteuerabzug gefährdet.

| Check | Was wird geprüft | Fehlermeldung bei |
|---|---|---|
| `pflichtfelder` | Alle 5 §14-Felder vorhanden? | Fehlendes Feld mit conf=0 |
| `iban_prüfziffer` | IBAN-Checksum korrekt (ISO 13616)? | Falsch berechnete Prüfziffer |
| `mwst_plausibel` | brutto ≈ netto × (1 + mwst_satz/100)? | Abweichung > 0,05 € |
| `mwst_satz_erlaubt` | Satz ist 0%, 7% oder 19%? | Andere Werte |
| `datum_format` | Datum parsebar und plausibel (±5 Jahre)? | Englisches Format, Zukunft |
| `betrag_vorzeichen` | Storno/Gutschrift haben negativen Betrag? | Positiver Betrag bei Storno |

---

## Schritt 1 — Validator schreiben (`src/validation.py`) (3–4h)

```python
# src/validation.py

def check_all(extraction: dict) -> list[dict]:
    """Gibt Liste von Check-Ergebnissen zurück."""
    results = []
    results += _check_pflichtfelder(extraction)
    results += [_check_iban(extraction)]
    results += [_check_mwst_plausibel(extraction)]
    results += [_check_mwst_satz_erlaubt(extraction)]
    results += [_check_datum_format(extraction)]
    results += [_check_betrag_vorzeichen(extraction)]
    return [r for r in results if r is not None]

PFLICHTFELDER_14 = [
    "rechnungsnummer", "datum", "betrag_brutto",
    "lieferant_name", "steuernummer"
]

def _check_pflichtfelder(extr: dict) -> list[dict]:
    results = []
    for feld in PFLICHTFELDER_14:
        if not extr.get(feld, {}).get("value"):
            results.append({
                "check_name": f"pflichtfeld_{feld}",
                "result": "fail",
                "detail": f"§14 UStG: Pflichtfeld '{feld}' fehlt"
            })
    return results

def _check_iban(extr: dict) -> dict | None:
    iban = extr.get("iban", {}).get("value")
    if not iban:
        return None   # kein IBAN → kein Check
    # ISO 13616 Prüfziffer: erste 4 Zeichen ans Ende, A=10…Z=35, mod 97 == 1
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    ok = int(numeric) % 97 == 1
    return {
        "check_name": "iban_prüfziffer",
        "result": "ok" if ok else "fail",
        "detail": None if ok else f"IBAN {iban} hat ungültige Prüfziffer"
    }

def _check_mwst_plausibel(extr: dict) -> dict | None:
    """brutto == netto + mwst, Toleranz 0,05 €"""
    def to_float(key):
        val = extr.get(key, {}).get("value")
        if not val:
            return None
        return float(val.replace(".", "").replace(",", "."))

    brutto = to_float("betrag_brutto")
    netto  = to_float("netto_betrag")
    mwst   = to_float("mwst_betrag")
    if None in (brutto, netto, mwst):
        return None
    diff = abs(abs(brutto) - (abs(netto) + abs(mwst)))
    ok = diff <= 0.05
    return {
        "check_name": "mwst_plausibel",
        "result": "ok" if ok else "warn",
        "detail": None if ok else f"Abweichung {diff:.2f} € (brutto={brutto}, netto={netto}, mwst={mwst})"
    }

def _check_mwst_satz_erlaubt(extr: dict) -> dict | None:
    satz = extr.get("mwst_satz", {}).get("value")
    if not satz:
        return None
    erlaubt = {"0", "7", "19", "0,00", "7,00", "19,00"}
    ok = satz.replace(",00", "") in erlaubt
    return {
        "check_name": "mwst_satz_erlaubt",
        "result": "ok" if ok else "warn",
        "detail": None if ok else f"Unüblicher MwSt-Satz: {satz}%"
    }

def _check_datum_format(extr: dict) -> dict | None:
    import re
    from datetime import datetime
    datum = extr.get("datum", {}).get("value")
    if not datum:
        return None
    # Nur deutsches TT.MM.JJJJ als "ok" — englisch = warn
    if re.match(r'\d{2}\.\d{2}\.\d{4}', datum):
        try:
            d = datetime.strptime(datum, "%d.%m.%Y")
            if 2015 <= d.year <= 2035:
                return {"check_name": "datum_format", "result": "ok", "detail": None}
        except ValueError:
            pass
    return {
        "check_name": "datum_format",
        "result": "warn",
        "detail": f"Datum nicht im deutschen Format oder unplausibel: '{datum}'"
    }

def _check_betrag_vorzeichen(extr: dict) -> dict | None:
    typ    = extr.get("dokumenttyp", {}).get("value")
    brutto = extr.get("betrag_brutto", {}).get("value")
    if not (typ and brutto):
        return None
    val = float(brutto.replace(".", "").replace(",", "."))
    if typ in ("storno", "gutschrift") and val > 0:
        return {
            "check_name": "betrag_vorzeichen",
            "result": "warn",
            "detail": f"Dokumenttyp '{typ}' hat positiven Bruttobetrag ({brutto})"
        }
    return {"check_name": "betrag_vorzeichen", "result": "ok", "detail": None}
```

---

## Schritt 2 — Validation in Ingestion integrieren (1h)

In `scripts/ingest_invoice.py` nach dem extractions-INSERT:

```python
from src.validation import check_all

checks = check_all(result)
for c in checks:
    cur.execute(
        "INSERT INTO validations (extraction_id, check_name, result, detail) "
        "VALUES (%s, %s, %s, %s)",
        (extr_id, c["check_name"], c["result"], c["detail"])
    )

fails = [c for c in checks if c["result"] == "fail"]
warns = [c for c in checks if c["result"] == "warn"]
print(f"Validierung: {len(checks)} Checks — {len(fails)} FAIL, {len(warns)} WARN")
```

---

## Schritt 3 — Alle 26 Rechnungen validieren + Ergebnisse auswerten (1–2h)

```bash
# Alle neu ingesten (DB vorher leeren oder Migration):
psql -h localhost -U postgres -d invoices -c "TRUNCATE documents CASCADE;"
for f in samples/realtestdata/*.pdf; do
    .venv/bin/python scripts/ingest_invoice.py "$f"
done

# Validierungsergebnisse: Übersicht
psql -h localhost -U postgres -d invoices -c "
SELECT check_name, result, COUNT(*) as n
FROM validations
GROUP BY 1, 2 ORDER BY 1, 2;"

# Alle FAILs anzeigen
psql -h localhost -U postgres -d invoices -c "
SELECT d.filename, v.check_name, v.detail
FROM validations v
JOIN extractions e ON e.id = v.extraction_id
JOIN documents   d ON d.id = e.document_id
WHERE v.result = 'fail'
ORDER BY d.filename, v.check_name;"
```

---

## Schritt 4 — Checkpoint: §14-Abdeckung

Ziel: alle 5 §14-Pflichtfelder auf möglichst vielen Rechnungen `ok`.

| Pflichtfeld | Aktuell | Ziel |
|---|---|---|
| rechnungsnummer | 100% | ✅ |
| datum | 100% | ✅ |
| betrag_brutto | 100% | ✅ |
| lieferant_name | 100% | ✅ |
| steuernummer | 65% | ⚠️ — strukturell (restliche Docs nur USt-ID) |

Dokumente die `steuernummer`-FAIL haben (congstar, STRATO, intersport, Amazon etc.)
bekommen in der späteren UI eine manuelle Eingabe-Möglichkeit.

---

## Schritt 5 — Commit (15 min)

```bash
git add src/validation.py scripts/ingest_invoice.py
git commit -m "feat: Woche 9-10 — §14-Validierung + IBAN-Prüfziffer + MwSt-Plausibilität"
```

**Woche 9–10 Ergebnis:** Jede Rechnung hat automatische Qualitäts-Checks.
Steuerberater sieht sofort: welche Rechnungen sind §14-konform, welche nicht.

---

## Danach: Woche 11–16 (Review UI)

```
Ziel: Human-in-the-Loop erzwingen
  → Einfache Web-UI (FastAPI + Jinja2 oder Streamlit)
  → Pro Rechnung: extrahierte Felder anzeigen, Confidence als Ampel
  → "Bestätigen"-Button: erst dann → confirmations INSERT
  → Kein DATEV-Export ohne Bestätigung (technisch erzwungen)
```

---

*Nächste Planungs-Datei: `PLAN_KW22-29_WOCHE11-16.md` (Review UI + DATEV Export)*
