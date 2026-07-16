"""app.py — FastAPI Review UI.

Routen-Vertrag (eingefroren nach B2.4):
  GET  /                       → Redirect auf /invoices
  GET  /invoices               → Liste aller Dokumente
  GET  /invoices/{id}          → Review-Detail
  GET  /invoices/{id}/pdf      → 307 → MinIO Presigned URL (1h TTL)
  POST /invoices/{id}/confirm  → confirmations INSERT
  POST /invoices/{id}/correct  → field_corrections INSERT
  GET  /export/datev           → DATEV CSV Download

Implementierung der Routen kommt in Phase UI.
"""

from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.db import get_conn
from src.review import confirm_extraction, is_confirmed, save_correction
from src.storage import get_object_bytes, presigned_url
from src.export.datev import generate_csv

_BASE = Path(__file__).parent

app = FastAPI(title="Rechnungserkennung Review UI", docs_url="/api/docs")
templates = Jinja2Templates(directory=str(_BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")


def _dtformat(value, fmt: str = "%d.%m.%Y %H:%M") -> str:
    if value is None:
        return "—"
    if isinstance(value, (datetime, date)):
        return value.strftime(fmt)
    return str(value)


templates.env.filters["dtformat"] = _dtformat


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/invoices")


# ---------------------------------------------------------------------------
# GET /invoices
# Response: [{id, filename, status, datum, lieferant_name, betrag_brutto,
#             dokumenttyp, fail_count, warn_count, is_confirmed}]
# ---------------------------------------------------------------------------
@app.get("/invoices")
async def invoice_list(
    request: Request,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    doc_type: str | None = Query(None, alias="type"),
    status: str | None = Query(None),
):
    conditions: list[str] = []
    params: list = []

    if date_from:
        conditions.append("e.datum >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("e.datum <= %s")
        params.append(date_to)
    if doc_type:
        conditions.append("LOWER(e.dokumenttyp) = LOWER(%s)")
        params.append(doc_type)
    if status == "confirmed":
        conditions.append("EXISTS(SELECT 1 FROM confirmations c WHERE c.extraction_id = e.id)")
    elif status == "pending":
        conditions.append("NOT EXISTS(SELECT 1 FROM confirmations c WHERE c.extraction_id = e.id)")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT
                d.id,
                d.filename,
                e.datum,
                e.lieferant_name,
                e.betrag_brutto,
                e.dokumenttyp,
                COUNT(v.*) FILTER (WHERE v.result = 'fail')  AS fail_count,
                COUNT(v.*) FILTER (WHERE v.result = 'warn')  AS warn_count,
                EXISTS(SELECT 1 FROM confirmations c WHERE c.extraction_id = e.id) AS is_confirmed
            FROM documents d
            JOIN extractions e ON e.document_id = d.id
            LEFT JOIN validations v ON v.extraction_id = e.id
            {where}
            GROUP BY d.id, d.filename, e.id
            ORDER BY e.datum DESC NULLS LAST, d.id
        """, params)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    return templates.TemplateResponse(
        request,
        "invoice_list.html",
        {
            "invoices": rows,
            "filters": {
                "date_from": date_from or "",
                "date_to": date_to or "",
                "doc_type": doc_type or "",
                "status": status or "",
            },
        },
    )


# ---------------------------------------------------------------------------
# GET /invoices/{id}
# Response: {document, extraction, effective_fields, validations,
#            corrections, confirmations, pdf_url}
# ---------------------------------------------------------------------------
@app.get("/invoices/{invoice_id}")
async def invoice_detail(request: Request, invoice_id: int):
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("SELECT * FROM documents WHERE id = %s", (invoice_id,))
        doc_cols = [d[0] for d in cur.description]
        doc_row = cur.fetchone()
        if not doc_row:
            return Response(status_code=404, content="Rechnung nicht gefunden")
        document = dict(zip(doc_cols, doc_row))

        cur.execute("SELECT * FROM extractions WHERE document_id = %s", (invoice_id,))
        ext_cols = [d[0] for d in cur.description]
        extraction = dict(zip(ext_cols, cur.fetchone()))

        cur.execute("SELECT * FROM v_effective_extractions WHERE document_id = %s", (invoice_id,))
        eff_cols = [d[0] for d in cur.description]
        effective = dict(zip(eff_cols, cur.fetchone()))

        cur.execute("SELECT * FROM validations WHERE extraction_id = %s ORDER BY id", (extraction["id"],))
        val_cols = [d[0] for d in cur.description]
        validations = [dict(zip(val_cols, r)) for r in cur.fetchall()]

        cur.execute(
            "SELECT * FROM field_corrections WHERE extraction_id = %s ORDER BY id",
            (extraction["id"],),
        )
        corr_cols = [d[0] for d in cur.description]
        corrections = [dict(zip(corr_cols, r)) for r in cur.fetchall()]

        cur.execute(
            "SELECT * FROM confirmations WHERE extraction_id = %s ORDER BY id",
            (extraction["id"],),
        )
        conf_cols = [d[0] for d in cur.description]
        confirmations_list = [dict(zip(conf_cols, r)) for r in cur.fetchall()]

    pdf_url = f"/invoices/{invoice_id}/pdf"

    return templates.TemplateResponse(
        request,
        "invoice_detail.html",
        {
            "document": document,
            "extraction": extraction,
            "effective": effective,
            "validations": validations,
            "corrections": corrections,
            "confirmations": confirmations_list,
            "pdf_url": pdf_url,
        },
    )


# ---------------------------------------------------------------------------
# GET /invoices/{id}/pdf → PDF direkt streamen (MinIO ist nur localhost)
# ---------------------------------------------------------------------------
@app.get("/invoices/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT minio_path, filename FROM documents WHERE id = %s", (invoice_id,))
        row = cur.fetchone()
    if not row:
        return Response(status_code=404)

    minio_path, filename = row
    object_name = minio_path.split("/", 1)[-1] if "/" in minio_path else minio_path
    data = get_object_bytes(object_name)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# POST /invoices/{id}/confirm
# Body: {confirmed_by: str, note: str|null}
# ---------------------------------------------------------------------------
@app.post("/invoices/{invoice_id}/confirm")
async def confirm_invoice(invoice_id: int, request: Request):
    body = await request.json()
    confirmed_by: str = body.get("confirmed_by", "").strip()
    note: str | None = body.get("note") or None

    if not confirmed_by:
        return Response(status_code=422, content="confirmed_by darf nicht leer sein")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM extractions WHERE document_id = %s", (invoice_id,))
        row = cur.fetchone()
    if not row:
        return Response(status_code=404)

    extraction_id = row[0]
    conf_id = confirm_extraction(extraction_id, confirmed_by, note)

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT confirmed_at FROM confirmations WHERE id = %s", (conf_id,))
        confirmed_at = cur.fetchone()[0]

    return {"confirmation_id": conf_id, "confirmed_at": confirmed_at.isoformat()}


# ---------------------------------------------------------------------------
# POST /invoices/{id}/correct
# Body: {field_name: str, value: str, corrected_by: str}
# ---------------------------------------------------------------------------
@app.post("/invoices/{invoice_id}/correct")
async def correct_invoice(invoice_id: int, request: Request):
    body = await request.json()
    field_name: str = body.get("field_name", "").strip()
    value: str = body.get("value", "").strip()
    corrected_by: str = body.get("corrected_by", "").strip()

    if not field_name or not corrected_by:
        return Response(status_code=422, content="field_name und corrected_by sind Pflicht")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM extractions WHERE document_id = %s", (invoice_id,))
        row = cur.fetchone()
    if not row:
        return Response(status_code=404)

    extraction_id = row[0]
    corr_id = save_correction(extraction_id, field_name, value, corrected_by)

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT corrected_at FROM field_corrections WHERE id = %s", (corr_id,))
        corrected_at = cur.fetchone()[0]

    return {"correction_id": corr_id, "corrected_at": corrected_at.isoformat()}


# ---------------------------------------------------------------------------
# GET /export/datev?from=YYYY-MM-DD&to=YYYY-MM-DD
# ---------------------------------------------------------------------------
@app.get("/export/datev")
async def export_datev(date_from: date | None = None, date_to: date | None = None):
    csv_bytes = generate_csv(date_from=date_from, date_to=date_to)
    filename = f"datev_export_{date.today().isoformat()}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
