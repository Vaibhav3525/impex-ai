"""
Day 12 — 11-Class Buyer Reply Intelligence & Response Processing API Router
PRD §8 & §10: Automated classification of incoming buyer responses, entity extraction,
CRM pipeline progression, and compliance reviewer validation.

Endpoints:
  POST   /api/v1/replies/incoming      — Ingest raw incoming email, classify, extract entities & update CRM
  GET    /api/v1/replies               — List classified replies with multi-criteria filtering
  GET    /api/v1/replies/{reply_id}    — Retrieve details of a specific reply
  PATCH  /api/v1/replies/{reply_id}/review — Human reviewer verification & classification override
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.lead import Lead
from app.models.deal import BuyerReply
from app.schemas.reply import (
    REPLY_CLASSES,
    IncomingReplyRequest,
    ReplyReviewRequest,
    BuyerReplyResponse,
)
from app.services.reply_classifier import classify_buyer_reply

router = APIRouter(prefix="/replies", tags=["Reply Intelligence & Processing"])


@router.post("/incoming", response_model=BuyerReplyResponse, status_code=status.HTTP_201_CREATED)
def process_incoming_reply(
    req: IncomingReplyRequest,
    db: Session = Depends(get_db),
):
    """
    Ingests an incoming buyer email response.
    1. Executes 11-class intent classification
    2. Extracts structured entities (product, quantity, target price, delivery port, payment method)
    3. Persists record to BuyerReply table
    4. Automatically advances Lead in CRM pipeline
    """
    lead = db.query(Lead).filter(Lead.lead_id == req.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID '{req.lead_id}' not found.")

    # Classify & Extract Entities
    result = classify_buyer_reply(subject=req.subject, raw_body=req.raw_body)

    # Save to database
    reply_obj = BuyerReply(
        lead_id=lead.lead_id,
        deal_id=req.deal_id,
        from_email=req.from_email,
        subject=req.subject,
        raw_body=req.raw_body,
        classification=result.classification,
        confidence_score=result.confidence_score,
        extracted_product=result.extracted_product,
        extracted_quantity=result.extracted_quantity,
        extracted_target_price=result.extracted_target_price,
        extracted_delivery_port=result.extracted_delivery_port,
        extracted_payment_method=result.extracted_payment_method,
        extracted_next_action=result.extracted_next_action,
        reviewed_by_human="PENDING",
    )
    db.add(reply_obj)

    # Advance Lead in CRM
    lead.outreach_status = "Replied"
    lead.pipeline_stage = result.suggested_pipeline_stage
    lead.updated_at = datetime.now(timezone.utc)

    # Append note to lead
    ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    reply_summary = (
        f"[Incoming Response at {ts_str}]: Class: {result.classification} "
        f"({result.confidence_score * 100:.0f}% confidence). Action: {result.extracted_next_action}"
    )
    if lead.notes:
        lead.notes = f"{lead.notes}\n{reply_summary}"
    else:
        lead.notes = reply_summary

    db.commit()
    db.refresh(reply_obj)
    return reply_obj


@router.get("", response_model=List[BuyerReplyResponse])
def list_replies(
    classification: Optional[str] = None,
    lead_id: Optional[str] = None,
    reviewed_status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Lists received buyer responses with intent and review filters."""
    query = db.query(BuyerReply)

    if classification:
        query = query.filter(BuyerReply.classification == classification)
    if lead_id:
        query = query.filter(BuyerReply.lead_id == lead_id)
    if reviewed_status:
        query = query.filter(BuyerReply.reviewed_by_human == reviewed_status)

    return query.order_by(desc(BuyerReply.received_at)).limit(limit).all()


@router.get("/{reply_id}", response_model=BuyerReplyResponse)
def get_reply(reply_id: int, db: Session = Depends(get_db)):
    """Retrieves full text and extracted entities of a specific buyer response."""
    reply_obj = db.query(BuyerReply).filter(BuyerReply.id == reply_id).first()
    if not reply_obj:
        raise HTTPException(status_code=404, detail=f"Reply record with ID '{reply_id}' not found.")
    return reply_obj


@router.patch("/{reply_id}/review", response_model=BuyerReplyResponse)
def review_reply_classification(
    reply_id: int,
    req: ReplyReviewRequest,
    db: Session = Depends(get_db),
):
    """
    Human Reviewer Override Endpoint.
    Validates or reclassifies an incoming response and logs compliance reviewer notes.
    """
    reply_obj = db.query(BuyerReply).filter(BuyerReply.id == reply_id).first()
    if not reply_obj:
        raise HTTPException(status_code=404, detail=f"Reply record with ID '{reply_id}' not found.")

    if req.classification_override:
        if req.classification_override not in REPLY_CLASSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid classification '{req.classification_override}'. Must be one of: {', '.join(REPLY_CLASSES)}"
            )
        reply_obj.classification = req.classification_override
        reply_obj.reviewed_by_human = "OVERRIDDEN"
    else:
        reply_obj.reviewed_by_human = "APPROVED"

    reply_obj.human_notes = f"Reviewed by {req.reviewer_name}: {req.human_notes}"
    db.commit()
    db.refresh(reply_obj)
    return reply_obj
