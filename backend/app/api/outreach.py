"""
Day 10 — Mode A Assisted Outreach & AI Email Queue API Router
PRD §6 & §10: Grounded email outreach workflow.
All generated emails require explicit human review and approval before dispatch.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.lead import Lead
from app.models.product_profile import ProductProfile
from app.models.outreach import OutreachEmail, SuppressionList
from app.schemas.outreach import (
    EmailComposeRequest,
    EmailApprovalRequest,
    EmailRejectionRequest,
    OutreachEmailResponse,
    SuppressionCreate,
    SuppressionResponse,
    OutreachQueueSummary,
)
from app.services.email_composer import compose_grounded_email

router = APIRouter(prefix="/outreach", tags=["Outreach & AI Personalization"])


def _check_suppression(db: Session, email: str):
    """Enforces suppression list guardrail."""
    if not email:
        return
    norm_email = email.lower().strip()
    suppressed = db.query(SuppressionList).filter(SuppressionList.email == norm_email).first()
    if suppressed:
        raise HTTPException(
            status_code=400,
            detail=f"Email '{email}' is suppressed: {suppressed.reason}. Outreach blocked."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Compose Grounded Outreach Email (Enters Mode A Review Queue)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{lead_id}/compose", response_model=OutreachEmailResponse, status_code=status.HTTP_201_CREATED)
def compose_outreach_email(
    lead_id: str,
    req: EmailComposeRequest,
    db: Session = Depends(get_db),
):
    """
    Composes a strictly grounded, personalized export email for a buyer lead.
    Enforces Mode A safety: created in 'Queued' status awaiting compliance signoff.
    """
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found.")

    if not lead.business_email:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot compose outreach email: Lead '{lead.company_name}' has no business email."
        )

    # Check suppression list
    _check_suppression(db, lead.business_email)

    # Fetch product profile
    prod = None
    if req.product_profile_id.isdigit():
        prod = db.query(ProductProfile).filter(ProductProfile.id == int(req.product_profile_id)).first()
    else:
        prod = db.query(ProductProfile).filter(ProductProfile.profile_id == req.product_profile_id).first()

    if not prod:
        raise HTTPException(status_code=404, detail=f"Product profile '{req.product_profile_id}' not found.")

    # Generate factually grounded email
    composed = compose_grounded_email(
        lead=lead,
        product=prod,
        sequence_step=req.sequence_step,
        custom_instructions=req.custom_instructions,
    )

    # Save to outreach_emails queue
    outreach_email = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        to_name=lead.contact_name,
        company_name=lead.company_name,
        country=lead.country,
        subject=composed["subject"],
        body_text=composed["body_text"],
        body_html=composed["body_html"],
        sequence_step=req.sequence_step,
        status="Queued",
        approval_mode="Assisted",
        confidence_score=composed["confidence_score"],
        grounding_evidence=composed["grounding_evidence"],
    )

    db.add(outreach_email)

    # Update lead status to Outreach Queued if currently earlier in pipeline
    if lead.pipeline_stage in {"Discovered", "Verified Candidate", "Qualified"}:
        lead.pipeline_stage = "Outreach Queued"
        lead.outreach_status = "Queued"

    db.commit()
    db.refresh(outreach_email)
    return outreach_email


# ─────────────────────────────────────────────────────────────────────────────
# 2. Mode A Assisted Queue Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/queue", response_model=OutreachQueueSummary)
def get_outreach_queue(
    status_filter: Optional[str] = Query("Queued", description="Queued | Approved | Rejected | Sent"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Returns emails pending human review and approval in Mode A.
    """
    total_queued = db.query(OutreachEmail).filter(OutreachEmail.status == "Queued").count()
    total_approved = db.query(OutreachEmail).filter(OutreachEmail.status == "Approved").count()
    total_rejected = db.query(OutreachEmail).filter(OutreachEmail.status == "Rejected").count()
    total_sent = db.query(OutreachEmail).filter(OutreachEmail.status == "Sent").count()

    query = db.query(OutreachEmail)
    if status_filter:
        query = query.filter(OutreachEmail.status == status_filter)

    pending_items = query.order_by(desc(OutreachEmail.created_at)).limit(limit).all()

    return OutreachQueueSummary(
        total_queued=total_queued,
        total_approved=total_approved,
        total_rejected=total_rejected,
        total_sent=total_sent,
        pending_emails=pending_items,
    )


@router.get("/emails/{email_id}", response_model=OutreachEmailResponse)
def get_email_details(email_id: str, db: Session = Depends(get_db)):
    """Fetch details of a queued or dispatched email."""
    email_obj = db.query(OutreachEmail).filter(OutreachEmail.email_id == email_id).first()
    if not email_obj:
        raise HTTPException(status_code=404, detail=f"Outreach email '{email_id}' not found.")
    return email_obj


@router.post("/emails/{email_id}/approve", response_model=OutreachEmailResponse)
def approve_outreach_email(
    email_id: str,
    req: EmailApprovalRequest,
    db: Session = Depends(get_db),
):
    """
    PRD Human-in-the-Loop Signoff.
    Approves a queued email for delivery. Permits optional edits to subject and body.
    """
    email_obj = db.query(OutreachEmail).filter(OutreachEmail.email_id == email_id).first()
    if not email_obj:
        raise HTTPException(status_code=404, detail=f"Outreach email '{email_id}' not found.")

    if email_obj.status == "Sent":
        raise HTTPException(status_code=400, detail="Cannot edit or approve an email that has already been dispatched.")

    if req.subject_override:
        email_obj.subject = req.subject_override
    if req.body_override:
        email_obj.body_text = req.body_override
        email_obj.body_html = f"<div style='font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;'>{req.body_override}</div>"

    email_obj.status = "Approved"
    email_obj.approved_by = req.reviewer_name
    email_obj.approved_at = datetime.now(timezone.utc)
    email_obj.updated_at = datetime.now(timezone.utc)

    # Update associated lead
    lead = db.query(Lead).filter(Lead.lead_id == email_obj.lead_id).first()
    if lead and lead.pipeline_stage in {"Discovered", "Verified Candidate", "Outreach Queued"}:
        lead.pipeline_stage = "Outreach Approved"

    db.commit()
    db.refresh(email_obj)
    return email_obj


@router.post("/emails/{email_id}/reject", response_model=OutreachEmailResponse)
def reject_outreach_email(
    email_id: str,
    req: EmailRejectionRequest,
    db: Session = Depends(get_db),
):
    """
    Rejects a queued email with an audit reason, preventing automated or manual dispatch.
    """
    email_obj = db.query(OutreachEmail).filter(OutreachEmail.email_id == email_id).first()
    if not email_obj:
        raise HTTPException(status_code=404, detail=f"Outreach email '{email_id}' not found.")

    email_obj.status = "Rejected"
    email_obj.rejection_reason = f"Rejected by {req.reviewer_name}: {req.reason}"
    email_obj.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(email_obj)
    return email_obj


# ─────────────────────────────────────────────────────────────────────────────
# 3. Suppression List Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/suppression", response_model=List[SuppressionResponse])
def list_suppression_list(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Lists all suppressed email addresses."""
    return db.query(SuppressionList).order_by(desc(SuppressionList.created_at)).limit(limit).all()


@router.post("/suppression", response_model=SuppressionResponse, status_code=status.HTTP_201_CREATED)
def add_to_suppression_list(
    supp_in: SuppressionCreate,
    db: Session = Depends(get_db),
):
    """Adds an email or domain to the suppression registry."""
    norm_email = supp_in.email.lower().strip()
    existing = db.query(SuppressionList).filter(SuppressionList.email == norm_email).first()
    if existing:
        return existing

    new_supp = SuppressionList(
        email=norm_email,
        reason=supp_in.reason,
        notes=supp_in.notes,
    )
    db.add(new_supp)
    db.commit()
    db.refresh(new_supp)
    return new_supp
