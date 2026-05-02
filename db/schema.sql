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

-- ---------------------------------------------------------------------------
-- B1.1 — ust_idnr (§14 UStG: USt-IdNr. als Alternative zur Steuernummer)
-- B1.2 — leistungsdatum (DATEV-Buchungsdatum bevorzugt gegenüber Rechnungsdatum)
-- B1.4 — docling_json_path (Bounding Boxes für späteres PDF-Highlighting, Woche 17+)
-- ---------------------------------------------------------------------------

ALTER TABLE extractions ADD COLUMN IF NOT EXISTS ust_idnr            TEXT;
ALTER TABLE extractions ADD COLUMN IF NOT EXISTS ust_idnr_conf       REAL;
ALTER TABLE extractions ADD COLUMN IF NOT EXISTS leistungsdatum      TEXT;
ALTER TABLE extractions ADD COLUMN IF NOT EXISTS leistungsdatum_conf REAL;
ALTER TABLE extractions ADD COLUMN IF NOT EXISTS docling_json_path   TEXT;

-- ---------------------------------------------------------------------------
-- B1.5 — field_corrections (GoBD: append-only manuelle Korrekturen)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS field_corrections (
    id               BIGSERIAL    PRIMARY KEY,
    extraction_id    BIGINT       NOT NULL REFERENCES extractions(id),
    field_name       TEXT         NOT NULL,
    corrected_value  TEXT         NOT NULL,
    corrected_by     TEXT         NOT NULL,
    corrected_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    note             TEXT
);

DROP TRIGGER IF EXISTS trg_audit_field_corrections ON field_corrections;

CREATE TRIGGER trg_audit_field_corrections
    AFTER INSERT ON field_corrections
    FOR EACH ROW EXECUTE FUNCTION fn_audit_insert();

-- ---------------------------------------------------------------------------
-- B1.5 — v_effective_extractions (pro Feld: Korrektur wenn vorhanden, sonst Original)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_effective_extractions AS
SELECT
    e.*,
    COALESCE(fc_rn.corrected_value,  e.rechnungsnummer)  AS eff_rechnungsnummer,
    COALESCE(fc_dt.corrected_value,  e.datum)             AS eff_datum,
    COALESCE(fc_bb.corrected_value,  e.betrag_brutto)     AS eff_betrag_brutto,
    COALESCE(fc_ln.corrected_value,  e.lieferant_name)    AS eff_lieferant_name,
    COALESCE(fc_sn.corrected_value,  e.steuernummer)      AS eff_steuernummer,
    COALESCE(fc_ui.corrected_value,  e.ust_idnr)          AS eff_ust_idnr,
    COALESCE(fc_ld.corrected_value,  e.leistungsdatum)    AS eff_leistungsdatum,
    COALESCE(fc_mb.corrected_value,  e.mwst_betrag)       AS eff_mwst_betrag,
    COALESCE(fc_ms.corrected_value,  e.mwst_satz)         AS eff_mwst_satz,
    COALESCE(fc_nb.corrected_value,  e.netto_betrag)      AS eff_netto_betrag,
    COALESCE(fc_ib.corrected_value,  e.iban)              AS eff_iban
FROM extractions e
LEFT JOIN field_corrections fc_rn ON fc_rn.extraction_id = e.id AND fc_rn.field_name = 'rechnungsnummer'
    AND fc_rn.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'rechnungsnummer')
LEFT JOIN field_corrections fc_dt ON fc_dt.extraction_id = e.id AND fc_dt.field_name = 'datum'
    AND fc_dt.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'datum')
LEFT JOIN field_corrections fc_bb ON fc_bb.extraction_id = e.id AND fc_bb.field_name = 'betrag_brutto'
    AND fc_bb.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'betrag_brutto')
LEFT JOIN field_corrections fc_ln ON fc_ln.extraction_id = e.id AND fc_ln.field_name = 'lieferant_name'
    AND fc_ln.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'lieferant_name')
LEFT JOIN field_corrections fc_sn ON fc_sn.extraction_id = e.id AND fc_sn.field_name = 'steuernummer'
    AND fc_sn.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'steuernummer')
LEFT JOIN field_corrections fc_ui ON fc_ui.extraction_id = e.id AND fc_ui.field_name = 'ust_idnr'
    AND fc_ui.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'ust_idnr')
LEFT JOIN field_corrections fc_ld ON fc_ld.extraction_id = e.id AND fc_ld.field_name = 'leistungsdatum'
    AND fc_ld.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'leistungsdatum')
LEFT JOIN field_corrections fc_mb ON fc_mb.extraction_id = e.id AND fc_mb.field_name = 'mwst_betrag'
    AND fc_mb.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'mwst_betrag')
LEFT JOIN field_corrections fc_ms ON fc_ms.extraction_id = e.id AND fc_ms.field_name = 'mwst_satz'
    AND fc_ms.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'mwst_satz')
LEFT JOIN field_corrections fc_nb ON fc_nb.extraction_id = e.id AND fc_nb.field_name = 'netto_betrag'
    AND fc_nb.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'netto_betrag')
LEFT JOIN field_corrections fc_ib ON fc_ib.extraction_id = e.id AND fc_ib.field_name = 'iban'
    AND fc_ib.id = (SELECT MAX(id) FROM field_corrections WHERE extraction_id = e.id AND field_name = 'iban');
