from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.core.database import get_db
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse, LeadPagination
from app.services.lead_service import ingest_lead
from app.services.verification_service import run_lead_verification

router = APIRouter(prefix="/leads", tags=["Buyer Leads"])

@router.get("", response_model=LeadPagination)
def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    country: Optional[str] = None,
    product_category: Optional[str] = None,
    verification_status: Optional[str] = None,
    pipeline_stage: Optional[str] = None,
    min_score: Optional[float] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieve paginated leads with comprehensive multi-criteria filtering."""
    query = db.query(Lead)

    if country:
        query = query.filter(Lead.country.ilike(f"%{country}%"))
    if product_category:
        query = query.filter(Lead.product_category.ilike(f"%{product_category}%"))
    if verification_status:
        query = query.filter(Lead.verification_status == verification_status)
    if pipeline_stage:
        query = query.filter(Lead.pipeline_stage == pipeline_stage)
    if min_score is not None:
        query = query.filter(Lead.buyer_score >= min_score)
    if search:
        search_filter = or_(
            Lead.company_name.ilike(f"%{search}%"),
            Lead.contact_name.ilike(f"%{search}%"),
            Lead.business_email.ilike(f"%{search}%"),
            Lead.city.ilike(f"%{search}%"),
        )
        query = query.filter(search_filter)

    total = query.count()
    items = (
        query.order_by(desc(Lead.buyer_score), desc(Lead.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return LeadPagination(total=total, page=page, page_size=page_size, items=items)

@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(lead_in: LeadCreate, auto_verify: bool = True, db: Session = Depends(get_db)):
    """Ingest a new lead with automatic duplicate detection and optional instant verification."""
    lead, created = ingest_lead(db, lead_in)
    if auto_verify:
        run_lead_verification(db, lead)
    return lead

@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    """Fetch complete lead record by unique Lead ID."""
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
    return lead

@router.post("/{lead_id}/verify")
def trigger_verification(lead_id: str, db: Session = Depends(get_db)):
    """Trigger the 100-point verification engine for a specific lead."""
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
    
    log = run_lead_verification(db, lead)
    return {
        "lead_id": lead.lead_id,
        "company_name": lead.company_name,
        "buyer_score": lead.buyer_score,
        "verification_status": lead.verification_status,
        "risk_flags": lead.risk_flags,
        "verification_log": {
            "identity_score": log.identity_score,
            "relevance_score": log.relevance_score,
            "website_score": log.website_score,
            "email_score": log.email_score,
            "import_evidence_score": log.import_evidence_score,
            "independent_score": log.independent_score,
            "total_score": log.total_score,
            "risk_level": log.risk_level,
            "summary": log.evidence_summary
        }
    }
