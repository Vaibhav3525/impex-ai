"""
Day 4 — Trade Discovery & Market Intelligence API Router
Endpoints:
  POST /api/v1/discover/comtrade           — Query UN Comtrade for top import markets
  POST /api/v1/discover/apeda             — Ingest APEDA directory rows
  POST /api/v1/discover/itp              — Ingest Indian Trade Portal leads
  POST /api/v1/discover/verify-website   — Ethical company website alive check
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.schemas.lead import LeadCreate
from app.services.lead_service import ingest_lead
from app.services.verification_service import run_lead_verification
from app.services.trade_connectors import (
    UNComtradeConnector,
    APEDADirectoryConnector,
    IndianTradePortalConnector,
    PublicWebConnector,
    DiscoveredLead,
)

router = APIRouter(prefix="/discover", tags=["Trade Discovery & Market Intelligence"])


# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────

class ComtradeRequest(BaseModel):
    hs_code: str = Field(..., description="HS code to query (e.g. '100630' for husked rice)")
    period: str = Field("2023", description="Trade year e.g. '2023'")
    reporter_country: str = Field("699", description="UN M49 code for India = 699")
    top_n: int = Field(20, ge=1, le=50)

class APEDAIngestRequest(BaseModel):
    rows: list[dict] = Field(..., description="List of APEDA directory records as dicts")
    auto_verify: bool = True
    auto_ingest: bool = True

class ITPIngestRequest(BaseModel):
    leads: list[dict] = Field(..., description="List of Indian Trade Portal inquiry records")
    auto_verify: bool = True
    auto_ingest: bool = True

class WebsiteVerifyRequest(BaseModel):
    url: str = Field(..., description="Company website URL to probe")
    company_name: Optional[str] = None


def _discovered_lead_to_create(dl: DiscoveredLead) -> LeadCreate:
    return LeadCreate(
        company_name=dl.company_name,
        country=dl.country,
        city=dl.city,
        website=dl.website,
        product_category=dl.product_category,
        contact_name=dl.contact_name,
        job_title=dl.job_title,
        business_email=dl.business_email,
        phone_number=dl.phone_number,
        source=dl.source,
        source_url=dl.source_url,
        import_evidence=dl.import_evidence,
        notes=dl.notes,
    )


def _ingest_discovered(
    discovered: list[DiscoveredLead],
    auto_verify: bool,
    db: Session
) -> dict:
    created, duplicates, errors = 0, 0, 0
    ingested_ids = []
    error_details = []

    for dl in discovered:
        try:
            lead_in = _discovered_lead_to_create(dl)
            lead, is_new = ingest_lead(db, lead_in)
            if is_new:
                created += 1
            else:
                duplicates += 1

            if auto_verify:
                run_lead_verification(db, lead)

            ingested_ids.append(lead.lead_id)
        except Exception as exc:
            errors += 1
            error_details.append(f"{dl.company_name}: {str(exc)[:150]}")

    return {
        "created": created,
        "duplicates": duplicates,
        "errors": errors,
        "lead_ids": ingested_ids,
        "error_details": error_details[:10],
    }


# ─────────────────────────────────────────────
# ENDPOINT 1 — UN Comtrade Market Intelligence
# ─────────────────────────────────────────────

@router.post("/comtrade")
def query_comtrade_markets(req: ComtradeRequest):
    """
    Query UN Comtrade for the top countries importing a given HS code from India.
    Returns MARKET-LEVEL statistics only — not individual buyer records.
    Results are used to prioritize which countries to search for buyers in.
    """
    connector = UNComtradeConnector(api_key=settings.UN_COMTRADE_API_KEY if hasattr(settings, "UN_COMTRADE_API_KEY") else "")
    markets = connector.get_top_importing_countries(
        hs_code=req.hs_code,
        period=req.period,
        reporter_country=req.reporter_country,
        top_n=req.top_n,
    )

    return {
        "hs_code": req.hs_code,
        "period": req.period,
        "source": "UN Comtrade Official API",
        "source_url": "https://comtradeplus.un.org/",
        "disclaimer": (
            "These are country-level trade flow statistics. "
            "They represent aggregate import volumes by country, NOT individual buyer companies. "
            "Use this data to prioritize which markets to focus your buyer search on."
        ),
        "top_import_markets": markets,
        "total_markets": len(markets),
    }


# ─────────────────────────────────────────────
# ENDPOINT 2 — APEDA Directory Ingestion
# ─────────────────────────────────────────────

@router.post("/apeda")
def ingest_apeda_directory(
    req: APEDAIngestRequest,
    db: Session = Depends(get_db),
):
    """
    Process buyer records from APEDA published international buyer directories.
    Accepts raw directory rows (from CSV/PDF-extracted data) and normalizes them.
    """
    if not req.rows:
        raise HTTPException(status_code=400, detail="No rows provided")
    if len(req.rows) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 rows per request")

    connector = APEDADirectoryConnector()
    discovered = connector.process_directory_rows(req.rows)

    if not discovered:
        return {
            "status": "no_valid_records",
            "message": "No valid leads could be extracted from the provided rows. "
                       "Ensure each row contains at minimum: company_name, country, and product.",
            "processed_rows": len(req.rows),
        }

    if not req.auto_ingest:
        return {
            "status": "preview",
            "discovered_leads": len(discovered),
            "preview": [
                {"company": d.company_name, "country": d.country, "product": d.product_category}
                for d in discovered[:20]
            ]
        }

    ingestion_result = _ingest_discovered(discovered, req.auto_verify, db)

    return {
        "status": "completed",
        "source": "APEDA International Buyer Directory",
        "processed_rows": len(req.rows),
        "valid_leads_found": len(discovered),
        **ingestion_result,
    }


# ─────────────────────────────────────────────
# ENDPOINT 3 — Indian Trade Portal Leads
# ─────────────────────────────────────────────

@router.post("/itp")
def ingest_itp_leads(
    req: ITPIngestRequest,
    db: Session = Depends(get_db),
):
    """
    Process buyer inquiry leads from the Indian Trade Portal.
    Accepts inquiry records and normalizes them into the lead pipeline.
    """
    if not req.leads:
        raise HTTPException(status_code=400, detail="No leads provided")
    if len(req.leads) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 records per request")

    connector = IndianTradePortalConnector()
    discovered = connector.process_bulk_leads(req.leads)

    if not discovered:
        return {
            "status": "no_valid_records",
            "message": "No valid leads extracted. Ensure each record has buyer_name and buyer_country.",
            "processed": len(req.leads),
        }

    if not req.auto_ingest:
        return {
            "status": "preview",
            "valid_leads": len(discovered),
            "preview": [
                {"company": d.company_name, "country": d.country, "product": d.product_category}
                for d in discovered[:20]
            ]
        }

    ingestion_result = _ingest_discovered(discovered, req.auto_verify, db)

    return {
        "status": "completed",
        "source": "Indian Trade Portal",
        "processed": len(req.leads),
        "valid_leads": len(discovered),
        **ingestion_result,
    }


# ─────────────────────────────────────────────
# ENDPOINT 4 — Ethical Company Website Check
# ─────────────────────────────────────────────

@router.post("/verify-website")
def verify_company_website(req: WebsiteVerifyRequest):
    """
    Perform an ethical company website alive check.
    Probes the public URL for HTTP status, TLS/HTTPS, page title,
    and any publicly listed contact emails.
    Respects robots.txt and applies a 1.5-second rate limit.
    """
    connector = PublicWebConnector(rate_limit_seconds=1.5)
    result = connector.check_website_alive(req.url)

    response = {
        "url": req.url,
        "company_name": req.company_name,
        **result,
        "verification_contribution": {
            "website_alive_score": 8 if result.get("alive") else 0,
            "https_bonus": 4 if result.get("https") else 0,
            "public_email_found": bool(result.get("detected_public_emails")),
            "notes": (
                "Website alive = +8 pts, HTTPS confirmed = +4 pts toward 100-point verification score"
                if result.get("alive") else
                "Website unreachable — 0 pts for Website & Identity Consistency criterion"
            ),
        }
    }

    return response
