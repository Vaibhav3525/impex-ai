"""
Day 3 — Batch Import API Router
Endpoints:
  POST /api/v1/import/csv   — Upload a CSV file of leads
  POST /api/v1/import/json  — Upload a JSON file of leads
  GET  /api/v1/import/template  — Download the official CSV template
"""
import io
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.lead import LeadCreate
from app.services.lead_service import ingest_lead
from app.services.verification_service import run_lead_verification
from app.services.batch_ingestion import (
    parse_csv_bytes, parse_json_bytes, validate_row,
    BatchImportResult, RowResult
)

router = APIRouter(prefix="/import", tags=["Batch Lead Ingestion"])

MAX_ROWS_PER_UPLOAD = 500  # PRD: max 500 new records/day
ALLOWED_CSV_CONTENT_TYPES = {
    "text/csv", "application/csv", "text/plain", "application/vnd.ms-excel",
    "application/octet-stream"
}
ALLOWED_JSON_CONTENT_TYPES = {
    "application/json", "text/json", "application/octet-stream"
}

CSV_TEMPLATE_ROWS = [
    ["company_name", "country", "city", "website", "product_category",
     "contact_name", "job_title", "business_email", "phone_number",
     "source", "source_url", "import_evidence", "notes"],
    ["Example Imports Ltd", "United Kingdom", "London",
     "https://example-imports.co.uk", "Basmati Rice",
     "Jane Smith", "Procurement Director", "j.smith@example-imports.co.uk",
     "+44 20 7946 0958", "APEDA International Buyer Directory",
     "https://apeda.gov.in/buyer-directory/uk.pdf",
     "Registered importer under UK Food Standards Agency", ""],
]


def _run_batch(
    rows: list[dict],
    source_name: str,
    auto_verify: bool,
    db: Session
) -> BatchImportResult:
    result = BatchImportResult(source_filename=source_name, total_rows=len(rows))

    for idx, raw_row in enumerate(rows):
        row_num = idx + 1
        cleaned, errors, warnings = validate_row(raw_row, row_num)

        if errors:
            result.errors += 1
            result.rows.append(RowResult(
                row_number=row_num,
                status="error",
                company_name=raw_row.get("company_name") or raw_row.get("name", ""),
                errors=errors,
                warnings=warnings,
            ))
            continue

        try:
            lead_in = LeadCreate(
                company_name=cleaned["company_name"],
                country=cleaned["country"],
                city=cleaned.get("city") or None,
                website=cleaned.get("website") or None,
                product_category=cleaned["product_category"],
                contact_name=cleaned.get("contact_name") or None,
                job_title=cleaned.get("job_title") or None,
                business_email=cleaned.get("business_email") or None,
                phone_number=cleaned.get("phone_number") or None,
                source=cleaned.get("source", source_name),
                source_url=cleaned.get("source_url") or None,
                import_evidence=cleaned.get("import_evidence") or None,
                notes=cleaned.get("notes") or None,
            )

            lead, is_created = ingest_lead(db, lead_in)

            if auto_verify:
                run_lead_verification(db, lead)

            if is_created:
                result.created += 1
                status_str = "created"
            else:
                result.duplicates += 1
                status_str = "duplicate"

            result.rows.append(RowResult(
                row_number=row_num,
                status=status_str,
                lead_id=lead.lead_id,
                company_name=lead.company_name,
                warnings=warnings,
            ))

        except Exception as exc:
            result.errors += 1
            result.rows.append(RowResult(
                row_number=row_num,
                status="error",
                company_name=cleaned.get("company_name", ""),
                errors=[f"Database error: {str(exc)[:200]}"],
                warnings=warnings,
            ))

    return result


@router.post("/csv", status_code=status.HTTP_200_OK)
def import_leads_csv(
    file: UploadFile = File(...),
    auto_verify: bool = True,
    db: Session = Depends(get_db),
):
    """
    Upload a CSV file of up to 500 buyer lead records.
    Returns a detailed per-row import result report.
    """
    content_type = (file.content_type or "").lower()
    filename = file.filename or "upload.csv"

    content = file.file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        rows = parse_csv_bytes(content)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse CSV: {str(exc)}"
        )

    if not rows:
        raise HTTPException(status_code=400, detail="CSV file contains no data rows")

    if len(rows) > MAX_ROWS_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Upload exceeds maximum allowed rows per batch ({MAX_ROWS_PER_UPLOAD}). "
                   f"Submitted: {len(rows)}. Split your file and re-upload."
        )

    result = _run_batch(rows, source_name=filename, auto_verify=auto_verify, db=db)

    return {
        "status": "completed",
        "summary": result.summary(),
        "rows": [
            {
                "row": r.row_number,
                "status": r.status,
                "lead_id": r.lead_id,
                "company": r.company_name,
                "errors": r.errors,
                "warnings": r.warnings,
            }
            for r in result.rows
        ]
    }


@router.post("/json", status_code=status.HTTP_200_OK)
def import_leads_json(
    file: UploadFile = File(...),
    auto_verify: bool = True,
    db: Session = Depends(get_db),
):
    """
    Upload a JSON file of up to 500 buyer lead records.
    Accepts a list of objects or {"leads": [...]} envelope.
    """
    content = file.file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        rows = parse_json_bytes(content)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse JSON: {str(exc)}"
        )

    if not rows:
        raise HTTPException(status_code=400, detail="JSON file contains no records")

    if len(rows) > MAX_ROWS_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Upload exceeds maximum allowed rows ({MAX_ROWS_PER_UPLOAD}). Submitted: {len(rows)}."
        )

    filename = file.filename or "upload.json"
    result = _run_batch(rows, source_name=filename, auto_verify=auto_verify, db=db)

    return {
        "status": "completed",
        "summary": result.summary(),
        "rows": [
            {
                "row": r.row_number,
                "status": r.status,
                "lead_id": r.lead_id,
                "company": r.company_name,
                "errors": r.errors,
                "warnings": r.warnings,
            }
            for r in result.rows
        ]
    }


@router.get("/template")
def download_csv_template():
    """
    Download the official lead import CSV template with all 20 supported fields
    and one example row pre-populated with field guidance.
    """
    output = io.StringIO()
    import csv as csv_module
    writer = csv_module.writer(output)
    for row in CSV_TEMPLATE_ROWS:
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=impex_lead_import_template.csv"
        }
    )
