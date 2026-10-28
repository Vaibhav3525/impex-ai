"""
Day 4 — Trade Discovery & Market Intelligence API Router
Day 5 — Domain Enrichment API Router

Endpoints:
  POST /api/v1/discover/comtrade           — Query UN Comtrade for top import markets
  POST /api/v1/discover/apeda             — Ingest APEDA directory rows
  POST /api/v1/discover/itp              — Ingest Indian Trade Portal leads
  POST /api/v1/discover/verify-website   — Ethical company website alive check
  POST /api/v1/discover/enrich-domain    — Full DNS/TLS/WHOIS/contact-page enrichment
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
from app.services.domain_enrichment import enrich_domain
from app.services.lead_discovery_crawler import LeadDiscoveryCrawler
from app.services.embassy_directory_connector import EmbassyDirectoryConnector
from app.services.linkedin_dork_service import LinkedInDorkService

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

class AutonomousSearchRequest(BaseModel):
    commodity: str = Field(..., description="Commodity or product line to search (e.g. 'Basmati Rice', 'Spices')")
    country: Optional[str] = Field("All", description="Target country or 'All'")
    sources: list[str] = Field(["directories", "embassy", "web"], description="Sources to query")
    limit: int = Field(25, ge=1, le=100)
    auto_ingest: bool = Field(True, description="Automatically ingest discovered leads into database")
    auto_verify: bool = Field(True, description="Run 100-point verification engine on ingested leads")

class EmbassySearchRequest(BaseModel):
    country: Optional[str] = Field("All", description="Target market country or 'All'")
    commodity: Optional[str] = Field(None, description="Optional commodity filter")
    auto_ingest: bool = Field(True, description="Ingest discovered leads into database")
    auto_verify: bool = Field(True, description="Run 100-point verification")

class LinkedInDorkRequest(BaseModel):
    commodity: str = Field(..., description="Export commodity or product line")
    country: str = Field(..., description="Target buyer market country")
    roles: Optional[list[str]] = Field(None, description="Custom buyer roles to target")



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



# ─────────────────────────────────────────────
# ENDPOINT 5 — Full Domain Enrichment
# ─────────────────────────────────────────────

class DomainEnrichRequest(BaseModel):
    domain_or_url: str = Field(
        ...,
        description="Domain, URL, or email to enrich (e.g. 'acme.de', 'https://acme.de', 'buyer@acme.de')"
    )
    lead_id: Optional[str] = Field(
        None,
        description="If provided, apply score deltas and new flags to this lead record"
    )
    run_smtp: bool = Field(True, description="Attempt SMTP EHLO probe on MX server")
    run_whois: bool = Field(True, description="Run WHOIS domain age lookup")
    run_contact_page: bool = Field(True, description="Scan company contact/about page")


@router.post("/enrich-domain")
def enrich_company_domain(
    req: DomainEnrichRequest,
    db: Session = Depends(get_db),
):
    """
    Run full technical domain enrichment:
      1. DNS MX lookup — confirms mail infrastructure exists
      2. SMTP EHLO probe — verifies mail server is live (port 25, no email sent)
      3. TLS/SSL certificate check — validity and days-to-expiry
      4. WHOIS domain age — flags domains < 90 days old
      5. Contact page scan — extracts contact links, LinkedIn URL, emails, addresses

    If lead_id is supplied, score deltas and new flags are applied to that lead's
    verification record.  The lead's buyer_score is recalculated accordingly.

    PRD guarantee: no fabricated data is stored.  All findings are labelled
    as 'automated evidence' with timestamps.
    """
    result = enrich_domain(
        domain_or_url=req.domain_or_url,
        run_smtp=req.run_smtp,
        run_whois=req.run_whois,
        run_contact=req.run_contact_page,
    )
    result_dict = result.to_dict()

    applied_to_lead: Optional[dict] = None

    if req.lead_id:
        from app.models.lead import Lead
        lead = db.query(Lead).filter(Lead.lead_id == req.lead_id).first()
        if not lead:
            raise HTTPException(
                status_code=404,
                detail=f"Lead {req.lead_id} not found"
            )

        # Apply score deltas to the existing buyer_score (clamped 0–100)
        new_score = lead.buyer_score or 0.0
        new_score += result.email_score_delta
        new_score += result.website_score_delta
        new_score += result.independent_score_delta
        new_score = round(max(0.0, min(100.0, new_score)), 1)

        # Merge new flags into existing risk flags
        existing_flags: list = list(lead.risk_flags or [])
        for flag in result.new_flags:
            if flag not in existing_flags:
                existing_flags.append(flag)

        # Update verification status based on new score
        from datetime import datetime, timezone
        if new_score >= 80.0 and "FLAG_FREE_EMAIL_DOMAIN" not in existing_flags:
            new_status = "Verified"
        elif new_score >= 60.0:
            new_status = "Partially Verified"
        else:
            new_status = "Unverified"

        lead.buyer_score = new_score
        lead.risk_flags = existing_flags
        lead.verification_status = new_status
        lead.last_verified = datetime.now(timezone.utc)

        # Append enrichment evidence to notes
        evidence_summary = " | ".join(result.evidence_notes[:5])
        if lead.notes:
            lead.notes = f"{lead.notes}\n[Day5 Enrichment] {evidence_summary}"
        else:
            lead.notes = f"[Day5 Enrichment] {evidence_summary}"

        db.commit()
        db.refresh(lead)

        applied_to_lead = {
            "lead_id": lead.lead_id,
            "company_name": lead.company_name,
            "new_buyer_score": new_score,
            "new_verification_status": new_status,
            "new_risk_flags": existing_flags,
        }

    return {
        "domain": result.domain,
        "enrichment": result_dict,
        "applied_to_lead": applied_to_lead,
        "disclaimer": (
            "All findings are automated technical checks. "
            "A passing check is a positive signal, not a guarantee of buyer legitimacy. "
            "A failing check is evidence for human review, not automatic disqualification."
        ),
    }


# ─────────────────────────────────────────────
# ENDPOINT 6 — Autonomous Lead Discovery Engine
# ─────────────────────────────────────────────

@router.post("/autonomous-search")
def run_autonomous_lead_discovery(
    req: AutonomousSearchRequest,
    db: Session = Depends(get_db)
):
    """
    PRD §3: Complete Autonomous Lead Generation Engine.
    Discovers candidate international buyers matching a commodity and target country across:
      1. Verified Global Importers Registry & Business Chambers
      2. Indian Embassy & MEA Commercial Mission Registries
      3. Public Corporate Web Directory Crawling
    Automatically validates structure, deduplicates via SHA-256, and runs 100-point verification.
    """
    discovered_leads: list[DiscoveredLead] = []

    # 1. Query Embassy Directories if requested
    if "embassy" in req.sources or "all" in req.sources:
        embassy_connector = EmbassyDirectoryConnector()
        c_filter = None if req.country == "All" else req.country
        emb_leads = embassy_connector.fetch_embassy_leads(country=c_filter, commodity=req.commodity)
        discovered_leads.extend(emb_leads)

    # 2. Query Autonomous Web Crawler & Global Importers Registry
    if "directories" in req.sources or "web" in req.sources or "all" in req.sources:
        crawler = LeadDiscoveryCrawler()
        c_filter = None if req.country == "All" else req.country
        crawl_leads = crawler.search_and_discover(
            commodity=req.commodity,
            country=c_filter,
            limit=req.limit
        )
        discovered_leads.extend(crawl_leads)

    # Deduplicate in memory before ingestion
    seen_keys = set()
    unique_discovered = []
    for dl in discovered_leads:
        key = (dl.company_name.lower().strip(), dl.country.lower().strip())
        if key not in seen_keys:
            seen_keys.add(key)
            unique_discovered.append(dl)

    limited_discovered = unique_discovered[:req.limit]

    # Ingest and verify if enabled
    ingest_summary = {}
    if req.auto_ingest:
        ingest_summary = _ingest_discovered(limited_discovered, req.auto_verify, db)

    return {
        "commodity": req.commodity,
        "country": req.country,
        "total_discovered": len(limited_discovered),
        "created_new_leads": ingest_summary.get("created", 0),
        "duplicate_leads_updated": ingest_summary.get("duplicates", 0),
        "ingested_lead_ids": ingest_summary.get("lead_ids", []),
        "leads": [
            {
                "company_name": l.company_name,
                "country": l.country,
                "city": l.city,
                "website": l.website,
                "product_category": l.product_category,
                "contact_name": l.contact_name,
                "job_title": l.job_title,
                "business_email": l.business_email,
                "phone_number": l.phone_number,
                "source": l.source,
                "source_url": l.source_url,
                "import_evidence": l.import_evidence
            }
            for l in limited_discovered
        ]
    }


# ─────────────────────────────────────────────
# ENDPOINT 7 — Indian Embassy Commercial Registries
# ─────────────────────────────────────────────

@router.post("/embassy-directories")
def search_embassy_directories(
    req: EmbassySearchRequest,
    db: Session = Depends(get_db)
):
    """
    Retrieves verified international buyers officially published by Indian Diplomatic Missions abroad.
    """
    connector = EmbassyDirectoryConnector()
    c_filter = None if req.country == "All" else req.country
    leads = connector.fetch_embassy_leads(country=c_filter, commodity=req.commodity)

    ingest_summary = {}
    if req.auto_ingest and leads:
        ingest_summary = _ingest_discovered(leads, req.auto_verify, db)

    return {
        "total_leads_found": len(leads),
        "created": ingest_summary.get("created", 0),
        "duplicates": ingest_summary.get("duplicates", 0),
        "leads": leads
    }


# ─────────────────────────────────────────────
# ENDPOINT 8 — LinkedIn Persona & X-Ray Search Engine
# ─────────────────────────────────────────────

@router.post("/linkedin-personas")
def generate_linkedin_xray_queries(req: LinkedInDorkRequest):
    """
    PRD §3.D: Lawfully generates targeted Google X-Ray search queries to identify
    specific buyer decision-makers (Import Managers, Procurement Directors)
    without unauthorized platform scraping or account bans.
    """
    service = LinkedInDorkService()
    result = service.generate_xray_queries(
        commodity=req.commodity,
        country=req.country,
        roles=req.roles
    )
    return result

