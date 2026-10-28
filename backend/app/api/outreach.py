"""
Day 10 & Day 11 — Mode A Assisted Outreach, Grounded AI Email Queue, & SMTP Dispatch API
PRD §6 & §10: Grounded email outreach workflow.
All generated emails require explicit human review and approval before dispatch.
Rate-limited SMTP transmission, hard-bounce auto-suppression, and delivery metrics.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
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
    FollowupProcessRequest,
    FollowupCadenceSummary,
    CadenceFunnelStatus,
)
from app.services.email_composer import compose_grounded_email
from app.services.smtp_service import (
    send_outreach_email,
    dispatch_approved_emails,
    get_send_window_metrics,
)
from app.services.followup_service import (
    process_all_due_followups,
    get_cadence_pipeline_status,
    generate_next_followup_email,
    cancel_pending_followups_for_lead,
    is_lead_eligible_for_followup,
)

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



# ─────────────────────────────────────────────────────────────────────────────
# 4. SMTP Dispatch & Rate-Limited Transmission Endpoints (Day 11)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_outreach_send_stats(db: Session = Depends(get_db)):
    """
    Returns real-time dispatch volume vs hourly and daily rate limits.
    """
    return get_send_window_metrics(db)


@router.post("/emails/{email_id}/send")
def dispatch_single_email(
    email_id: str,
    bypass_rate_limits: bool = False,
    db: Session = Depends(get_db),
):
    """
    Dispatches a single approved email via SMTP.
    Enforces Mode A approval validation, suppression check, and rate caps.
    """
    res = send_outreach_email(db, email_id, bypass_rate_limits=bypass_rate_limits)
    if not res.get("success"):
        raise HTTPException(
            status_code=400 if "Violation" in res.get("error", "") or "suppression" in res.get("error", "") else 429,
            detail=res.get("error")
        )
    return res


@router.post("/dispatch-batch")
def dispatch_approved_batch(
    max_emails: Optional[int] = Query(None, ge=1, le=50, description="Max emails to dispatch in this batch"),
    bypass_rate_limits: bool = False,
    db: Session = Depends(get_db),
):
    """
    Batches and dispatches pending approved emails up to remaining hourly/daily quota.
    """
    return dispatch_approved_emails(db, max_emails=max_emails, bypass_rate_limits=bypass_rate_limits)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Autonomous Follow-Up Cadence Engine (PRD §7)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/followups/status", response_model=CadenceFunnelStatus)
def get_cadence_status(db: Session = Depends(get_db)):
    """
    PRD §7: Returns real-time metrics across all 3 cadence touches:
    Touch 1 Sent -> Touch 2 Follow-Up -> Touch 3 Closing Inquiry -> Replied / Suppressed.
    """
    return get_cadence_pipeline_status(db)


@router.post("/followups/process", response_model=FollowupCadenceSummary)
def process_due_followups_endpoint(
    req: FollowupProcessRequest,
    db: Session = Depends(get_db),
):
    """
    PRD §7: Autonomous Cadence Orchestrator.
    Scans for leads whose next follow-up touch (Touch 2 after 4 days, Touch 3 after 8 days)
    is due and creates grounded follow-up emails in the review queue.
    """
    res = process_all_due_followups(
        db=db,
        min_days=req.min_days,
        force_advance=req.force_advance,
        limit=req.limit,
    )
    return FollowupCadenceSummary(
        eligible_leads=res["eligible_leads"],
        generated_count=res["generated_count"],
        generated_emails=res["generated_emails"],
        skipped_reasons=res["skipped_reasons"],
    )


@router.post("/followups/{lead_id}/schedule-next", response_model=OutreachEmailResponse)
def schedule_lead_next_followup(
    lead_id: str,
    force: bool = Query(False, description="Bypass elapsed cadence interval (for testing or urgent touch)"),
    min_days: int = Query(4, ge=0, le=30, description="Minimum days required between touches"),
    custom_instructions: Optional[str] = Query(None, description="Optional custom commercial note"),
    db: Session = Depends(get_db),
):
    """
    Manually triggers generation of the next grounded follow-up sequence for a specific lead.
    """
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found.")

    eligible, reason = is_lead_eligible_for_followup(lead, db)
    if not eligible:
        raise HTTPException(status_code=400, detail=f"Lead not eligible for follow-up: {reason}")

    email_obj = generate_next_followup_email(
        db=db,
        lead_id=lead_id,
        min_days=min_days,
        force=force,
        custom_instructions=custom_instructions,
    )
    if not email_obj:
        raise HTTPException(
            status_code=400,
            detail=f"Follow-up not generated. Required interval ({min_days} days) may not have elapsed yet."
        )

    return email_obj


@router.post("/followups/{lead_id}/cancel")
def cancel_lead_followups(
    lead_id: str,
    reason: str = Query("Manual Cancellation", description="Reason for stopping cadence"),
    db: Session = Depends(get_db),
):
    """
    Manually halts and suppresses all active/queued follow-ups for a specific lead.
    """
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found.")

    cancelled = cancel_pending_followups_for_lead(db, lead_id, reason=reason)
    return {
        "lead_id": lead_id,
        "cancelled_count": cancelled,
        "status": "Halted",
        "reason": reason,
    }

