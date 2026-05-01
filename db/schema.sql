-- schema.sql
-- Append-only Schema für GoBD-konforme Rechnungsverarbeitung.
-- Kein UPDATE/DELETE auf documents/extractions — Trigger erzwingt das.
-- Korrekturen = neuer Eintrag, nicht Überschreiben.

-- ---------------------------------------------------------------------------
-- Kerntabellen
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS documents (
    id           BIGSERIAL    PRIMARY KEY,
    sha256       CHAR(64)     NOT NULL UNIQUE,   -- Duplikat-Schutz auf DB-Ebene
    filename     TEXT         NOT NULL,
    minio_path   TEXT         NOT NULL,
    status       TEXT         NOT NULL DEFAULT 'uploaded',
    retain_until DATE         NOT NULL,          -- Einlieferungsdatum + 10 Jahre (GoBD §14b)
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS extractions (
    id                    BIGSERIAL    PRIMARY KEY,
    document_id           BIGINT       NOT NULL REFERENCES documents(id),
    engine_version        TEXT         NOT NULL DEFAULT 'rule_engine_v1',
    -- Felder + Confidence-Scores (alle TEXT — Normalisierung in Woche 9)
    rechnungsnummer       TEXT,   rechnungsnummer_conf  REAL,
    datum                 TEXT,   datum_conf            REAL,
    betrag_brutto         TEXT,   betrag_brutto_conf    REAL,
    mwst_betrag           TEXT,   mwst_betrag_conf      REAL,
    netto_betrag          TEXT,   netto_betrag_conf     REAL,
    mwst_satz             TEXT,   mwst_satz_conf        REAL,
    dokumenttyp           TEXT,   dokumenttyp_conf      REAL,
    lieferant_name        TEXT,   lieferant_name_conf   REAL,
    steuernummer          TEXT,   steuernummer_conf     REAL,
    iban                  TEXT,   iban_conf             REAL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS validations (
    id              BIGSERIAL    PRIMARY KEY,
    extraction_id   BIGINT       NOT NULL REFERENCES extractions(id),
    check_name      TEXT         NOT NULL,
    result          TEXT         NOT NULL CHECK (result IN ('ok', 'warn', 'fail')),
    detail          TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS confirmations (
    id              BIGSERIAL    PRIMARY KEY,
    extraction_id   BIGINT       NOT NULL REFERENCES extractions(id),
    confirmed_by    TEXT         NOT NULL,
    confirmed_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    note            TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL    PRIMARY KEY,
    table_name  TEXT         NOT NULL,
    row_id      BIGINT       NOT NULL,
    action      TEXT         NOT NULL,
    payload     JSONB        NOT NULL,
    logged_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Trigger: audit_log automatisch befüllen bei jedem INSERT
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_audit_insert()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO audit_log(table_name, row_id, action, payload)
    VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW)::jsonb);
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_documents   ON documents;
DROP TRIGGER IF EXISTS trg_audit_extractions ON extractions;

CREATE TRIGGER trg_audit_documents
    AFTER INSERT ON documents
    FOR EACH ROW EXECUTE FUNCTION fn_audit_insert();

CREATE TRIGGER trg_audit_extractions
    AFTER INSERT ON extractions
    FOR EACH ROW EXECUTE FUNCTION fn_audit_insert();

-- ---------------------------------------------------------------------------
-- Trigger: UPDATE/DELETE auf documents und extractions verbieten (GoBD)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_no_update_delete()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        'UPDATE/DELETE auf "%" ist verboten — GoBD append-only (§14b UStG)',
        TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS trg_no_update_documents   ON documents;
DROP TRIGGER IF EXISTS trg_no_update_extractions ON extractions;

CREATE TRIGGER trg_no_update_documents
    BEFORE UPDATE OR DELETE ON documents
    FOR EACH ROW EXECUTE FUNCTION fn_no_update_delete();

CREATE TRIGGER trg_no_update_extractions
    BEFORE UPDATE OR DELETE ON extractions
    FOR EACH ROW EXECUTE FUNCTION fn_no_update_delete();
