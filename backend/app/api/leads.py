"""
Day 2, Day 7, Day 8 — Buyer Leads, 100-Point Verification, & Payment Risk Guardian API
Endpoints:
  GET    /api/v1/leads                     — Paginated listing with multi-criteria filtering
  POST   /api/v1/leads                     — Ingest new lead with deduplication
  GET    /api/v1/leads/review-queue        — PRD §4: Manual review queue for uncertain/flagged cases
  GET    /api/v1/leads/high-risk           — PRD §11: High & Critical payment risk monitor
  POST   /api/v1/leads/verify-batch        — PRD §5: High-throughput batch verification (up to 500/day)
  GET    /api/v1/leads/{lead_id}           — Fetch single lead by Lead ID
  POST   /api/v1/leads/{lead_id}/verify    — Trigger 100-point automated audit
  POST   /api/v1/leads/{lead_id}/verify-manual — Human reviewer override with full audit trail
  GET    /api/v1/leads/{lead_id}/audit-trail   — Complete verification history & evidence logs
  POST   /api/v1/leads/{lead_id}/risk-assessment — Run payment fraud and risk assessment
  GET    /api/v1/leads/{lead_id}/risk-assessment — Retrieve latest risk assessment
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.models.lead import Lead
from app.models.verification import VerificationLog
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadPagination,
    ManualVerificationRequest,
    BatchVerifyRequest,
    BatchVerifyResponse,
    VerificationLogResponse,
    RiskAssessmentResponse,
)
from app.services.lead_service import ingest_lead
from app.services.verification_service import run_lead_verification
from app.services.risk_service import (
    evaluate_lead_payment_risk,
    audit_and_save_lead_risk,
)

router = APIRouter(prefix="/leads", tags=["Buyer Leads & Verification"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Lead Listing & Creation
# ─────────────────────────────────────────────────────────────────────────────

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
        run_lead_verification(db, lead, run_live_checks=False)
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# 2. Review Queue & Batch Verification (Registered BEFORE /{lead_id})
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/review-queue", response_model=List[LeadResponse])
def get_manual_review_queue(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    PRD §4: Manual Review Queue for uncertain cases and flagged buyers.
    Retrieves leads that require compliance officer inspection:
      - Verification status is 'Partially Verified' (score 60-79)
      - Leads with active risk flags (e.g. free email, missing website, suspicious terms)
      - Leads flagged for manual review
    """
    leads = (
        db.query(Lead)
        .filter(
            or_(
                Lead.verification_status == "Partially Verified",
                Lead.verification_status == "Unverified",
                Lead.notes.ilike("%manual review%"),
                Lead.notes.ilike("%risk%"),
            )
        )
        .order_by(desc(Lead.created_at))
        .limit(limit)
        .all()
    )
    return leads


@router.get("/high-risk", response_model=List[LeadResponse])
def get_high_risk_leads(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    PRD §11: High & Critical Payment Risk Monitor.
    Retrieves all leads classified with HIGH or CRITICAL risk level,
    or with payment_risk_score >= 40.0.
    These buyers must never receive automated outreach without human authorization.
    """
    leads = (
        db.query(Lead)
        .filter(
            or_(
                Lead.risk_level == "CRITICAL",
                Lead.risk_level == "HIGH",
                Lead.payment_risk_score >= 40.0,
            )
        )
        .order_by(desc(Lead.payment_risk_score), desc(Lead.created_at))
        .limit(limit)
        .all()
    )
    return leads


@router.post("/verify-batch", response_model=BatchVerifyResponse)
def verify_batch_leads(
    req: BatchVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    PRD §5: High-throughput batch verification engine.
    Supports processing batches of discovered buyer records (up to 500/day).
    Evaluates evidence, calculates 100-point scores, and updates pipeline standing.
    """
    query = db.query(Lead)
    if req.only_unverified:
        query = query.filter(Lead.verification_status == "Unverified")

    leads_to_process = query.order_by(Lead.created_at.asc()).limit(req.limit).all()

    verified_count = 0
    partially_verified_count = 0
    unverified_count = 0
    total_score_sum = 0.0
    details: List[Dict[str, Any]] = []

    for lead in leads_to_process:
        log = run_lead_verification(db, lead, run_live_checks=req.run_live_checks)
        total_score_sum += log.total_score

        if lead.verification_status == "Verified":
            verified_count += 1
        elif lead.verification_status == "Partially Verified":
            partially_verified_count += 1
        else:
            unverified_count += 1

        details.append({
            "lead_id": lead.lead_id,
            "company_name": lead.company_name,
            "score": log.total_score,
            "status": lead.verification_status,
            "risk_level": log.risk_level,
            "flags": log.detected_flags or [],
        })

    total_processed = len(leads_to_process)
    avg_score = round(total_score_sum / total_processed, 1) if total_processed > 0 else 0.0

    return BatchVerifyResponse(
        total_processed=total_processed,
        verified_count=verified_count,
        partially_verified_count=partially_verified_count,
        unverified_count=unverified_count,
        average_score=avg_score,
        results=details,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Individual Lead Operations
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    """Fetch complete lead record by unique Lead ID."""
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
    return lead


@router.post("/{lead_id}/verify")
def trigger_verification(
    lead_id: str,
    run_live_checks: bool = Query(True, description="Execute live DNS MX and TLS socket checks"),
    db: Session = Depends(get_db),
):
    """Trigger the 100-point verification engine for a specific lead."""
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
    
    log = run_lead_verification(db, lead, run_live_checks=run_live_checks)
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
            "dns_mx_records": log.dns_mx_records,
            "ssl_valid": log.ssl_valid,
            "domain_age_days": log.domain_age_days,
            "verified_by": log.verified_by,
            "summary": log.evidence_summary,
        }
    }


@router.post("/{lead_id}/verify-manual", response_model=LeadResponse)
def manual_lead_verification_override(
    lead_id: str,
    req: ManualVerificationRequest,
    db: Session = Depends(get_db),
):
    """
    PRD §4 Human-in-the-Loop Override Endpoint.
    Enables compliance officers to inspect uncertain leads, clear false-positive flags,
    adjust buyer scores based on verified documentary evidence, and approve or reject.
    Maintains a tamper-evident audit trail in VerificationLog.
    """
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")

    # Update flags
    current_flags = list(lead.risk_flags or [])
    if req.cleared_flags:
        current_flags = [f for f in current_flags if f not in req.cleared_flags]
    if req.added_flags:
        for f in req.added_flags:
            if f not in current_flags:
                current_flags.append(f)
    lead.risk_flags = current_flags

    # Apply score adjustments
    if req.score_adjustment is not None:
        new_score = (lead.buyer_score or 0.0) + req.score_adjustment
        lead.buyer_score = round(max(0.0, min(100.0, new_score)), 1)

    # Apply status override
    if req.status_override:
        valid_statuses = {"Verified", "Partially Verified", "Unverified", "Rejected"}
        if req.status_override not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{req.status_override}'. Must be one of {valid_statuses}."
            )
        lead.verification_status = req.status_override
        if req.status_override == "Verified" and lead.pipeline_stage in {"Discovered", "Unverified"}:
            lead.pipeline_stage = "Verified Candidate"

    lead.last_verified = datetime.now(timezone.utc)

    # Append audit trail note
    audit_note = (
        f"[Manual Review by {req.reviewer_name} at {lead.last_verified.strftime('%Y-%m-%d %H:%M:%S UTC')}]: "
        f"{req.notes} | Status: {lead.verification_status} | Score: {lead.buyer_score}"
    )
    if lead.notes:
        lead.notes = f"{lead.notes}\n{audit_note}"
    else:
        lead.notes = audit_note

    # Create immutable VerificationLog entry for the manual override
    manual_log = VerificationLog(
        lead_id=lead.lead_id,
        identity_score=lead.buyer_score * 0.20,
        relevance_score=lead.buyer_score * 0.20,
        website_score=lead.buyer_score * 0.15,
        email_score=lead.buyer_score * 0.15,
        import_evidence_score=lead.buyer_score * 0.15,
        independent_score=lead.buyer_score * 0.15,
        total_score=lead.buyer_score,
        risk_level="LOW" if lead.verification_status == "Verified" else "MEDIUM",
        detected_flags=lead.risk_flags,
        verified_by=f"human_reviewer:{req.reviewer_name}",
        evidence_summary=f"Human review override by {req.reviewer_name}: {req.notes}",
    )
    db.add(manual_log)
    db.commit()
    db.refresh(lead)

    return lead


@router.get("/{lead_id}/audit-trail", response_model=List[VerificationLogResponse])
def get_lead_audit_trail(lead_id: str, db: Session = Depends(get_db)):
    """
    Returns the complete verification audit history for this lead,
    including both automated verification evaluations and human compliance overrides.
    """
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")

    logs = (
        db.query(VerificationLog)
        .filter(VerificationLog.lead_id == lead_id)
        .order_by(desc(VerificationLog.created_at))
        .all()
    )
    return logs


# ─────────────────────────────────────────────────────────────────────────────
# 4. Payment Risk Guardian Endpoints (Day 8)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{lead_id}/risk-assessment", response_model=RiskAssessmentResponse)
def evaluate_and_persist_risk(
    lead_id: str,
    db: Session = Depends(get_db),
):
    """
    PRD §11: Evaluates payment fraud indicators, advance-fee scam signals,
    country/website inconsistencies, and assigns dedicated payment_risk_score.
    Persists risk assessment to database.
    """
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")

    return audit_and_save_lead_risk(db, lead)


@router.get("/{lead_id}/risk-assessment", response_model=RiskAssessmentResponse)
def get_lead_risk_assessment(
    lead_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves the comprehensive payment risk assessment for a specific buyer.
    Evaluates current risk state without persisting changes.
    """
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")

    return evaluate_lead_payment_risk(lead)
