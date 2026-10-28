"""
Day 12 Tests — 11-Class Buyer Reply Intelligence & Entity Extraction Engine
Tests:
  - 11-class intent classification (RFQ, Samples, Negotiation, Scam, Opt-out, etc.)
  - Entity extraction (Product, Quantity, Target Price, Delivery Port, Payment Method)
  - Next action recommendations
  - Automated CRM pipeline stage advancement
  - Human review override and verification workflow
"""

import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.models.deal import BuyerReply
from app.schemas.lead import LeadCreate
from app.schemas.reply import (
    IncomingReplyRequest,
    ReplyReviewRequest,
)
from app.services.lead_service import ingest_lead
from app.services.reply_classifier import (
    classify_buyer_reply,
    _extract_quantity,
    _extract_target_price,
    _extract_delivery_port,
    _extract_payment_method,
)
from app.api.replies import (
    process_incoming_reply,
    list_replies,
    get_reply,
    review_reply_classification,
)


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _make_reply_lead(db: Session) -> Lead:
    uid = uuid.uuid4().hex[:6]
    lc = LeadCreate(
        company_name=f"Hanseatic Grains AG {uid}",
        country="Germany",
        city="Hamburg",
        website=f"https://hanseatic-{uid}.de",
        product_category="Basmati Rice & Spices",
        contact_name="Dirk Hoffman",
        job_title="Import Manager",
        business_email=f"hoffman@{uid}-hanseatic.de",
        phone_number="+49 40 987654",
        source="Hamburg Chamber of Commerce",
        source_url="https://hk24.de",
        import_evidence="Major grain importer in Northern Europe.",
    )
    lead, _ = ingest_lead(db, lc)
    lead.pipeline_stage = "Email Sent"
    db.commit()
    db.refresh(lead)
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# 1. 11-Class Classification & Intent Recognition
# ─────────────────────────────────────────────────────────────────────────────

def test_rfq_classification_and_entity_extraction():
    subject = "Re: Export Inquiry - Basmati Rice Supply"
    body = """Dear Sales Team,
Thank you for reaching out. Please quote us your best CIF price for 100 MT of 1121 Basmati Rice to Hamburg port.
We prefer 100% Irrevocable LC at Sight. We look forward to receiving your proforma quotation.
Regards, Dirk Hoffman"""

    res = classify_buyer_reply(subject, body)
    assert res.classification == "Request for Quotation"
    assert res.confidence_score >= 0.85
    assert res.extracted_quantity == "100 MT"
    assert res.extracted_delivery_port == "Hamburg"
    assert res.extracted_product == "Basmati Rice"
    assert "LC at Sight" in (res.extracted_payment_method or "")
    assert res.suggested_pipeline_stage == "Requirements Received"
    assert "Hamburg" in res.extracted_next_action


def test_samples_request_classification():
    subject = "Sample dispatch for Alleppey Green Cardamom"
    body = "Please courier a 1kg lab sample of extra bold cardamom to our Rotterdam office for quality evaluation."

    res = classify_buyer_reply(subject, body)
    assert res.classification == "Samples"
    assert res.extracted_delivery_port == "Rotterdam"
    assert res.suggested_pipeline_stage == "Requirements Received"
    assert "Dispatch representative courier sample" in res.extracted_next_action


def test_price_negotiation_classification():
    subject = "Re: Quotation review"
    body = "Your quotation of $1,280 is too expensive compared to Pakistan origin. Our target price is USD 1,120 per MT CIF Jebel Ali."

    res = classify_buyer_reply(subject, body)
    assert res.classification == "Price Negotiation"
    assert res.extracted_target_price == 1120.0
    assert res.extracted_delivery_port == "Jebel Ali"
    assert res.suggested_pipeline_stage == "Negotiation"


def test_scam_detection():
    subject = "Urgent: Contract tender registration fee"
    body = "To proceed with this procurement tender, you must wire an advance fee of $650 via Western Union for ministerial approval."

    res = classify_buyer_reply(subject, body)
    assert res.classification == "Potential Scam"
    assert res.suggested_pipeline_stage == "Lost / Rejected"
    assert "Security Alert" in res.extracted_next_action


def test_not_interested_opt_out():
    subject = "Unsubscribe"
    body = "We are not interested. Please remove us from your email list."

    res = classify_buyer_reply(subject, body)
    assert res.classification == "Not Interested"
    assert res.suggested_pipeline_stage == "Lost / Rejected"


def test_wrong_contact_classification():
    subject = "Wrong department"
    body = "I am no longer with the grain purchasing group. Please contact our purchasing department at buyers@example.com."

    res = classify_buyer_reply(subject, body)
    assert res.classification == "Wrong Contact"
    assert res.suggested_pipeline_stage == "Contacted"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Ingest API & Automated CRM Pipeline Progression
# ─────────────────────────────────────────────────────────────────────────────

def test_process_incoming_reply_api(db_session):
    lead = _make_reply_lead(db_session)
    assert lead.pipeline_stage == "Email Sent"

    req = IncomingReplyRequest(
        lead_id=lead.lead_id,
        from_email=lead.business_email,
        subject="Re: Quotation Request",
        raw_body="Please send quotation for 50 MT basmati rice CIF Antwerp port under irrevocable LC.",
    )
    reply_obj = process_incoming_reply(req=req, db=db_session)

    assert reply_obj.id is not None
    assert reply_obj.classification == "Request for Quotation"
    assert reply_obj.extracted_quantity == "50 MT"
    assert reply_obj.extracted_delivery_port == "Antwerp"
    assert reply_obj.reviewed_by_human == "PENDING"

    # Verify that the lead in CRM moved to 'Requirements Received'
    db_session.refresh(lead)
    assert lead.outreach_status == "Replied"
    assert lead.pipeline_stage == "Requirements Received"
    assert "Incoming Response" in lead.notes


# ─────────────────────────────────────────────────────────────────────────────
# 3. Human Review & Verification Workflow
# ─────────────────────────────────────────────────────────────────────────────

def test_human_reviewer_override_flow(db_session):
    lead = _make_reply_lead(db_session)

    # Ingest a reply
    req = IncomingReplyRequest(
        lead_id=lead.lead_id,
        from_email=lead.business_email,
        subject="Regarding our discussion",
        raw_body="We might be interested next season, but could you also quote us 20 MT today?",
    )
    reply_obj = process_incoming_reply(req=req, db=db_session)

    # Human reviewer inspects and reclassifies to RFQ
    review_req = ReplyReviewRequest(
        reviewer_name="Senior Sales Manager",
        classification_override="Request for Quotation",
        human_notes="Client asked for immediate quote on 20 MT despite mentioning future season.",
    )
    updated = review_reply_classification(reply_id=reply_obj.id, req=review_req, db=db_session)

    assert updated.classification == "Request for Quotation"
    assert updated.reviewed_by_human == "OVERRIDDEN"
    assert "Senior Sales Manager" in updated.human_notes


def test_list_and_filter_replies_api(db_session):
    lead = _make_reply_lead(db_session)
    req = IncomingReplyRequest(
        lead_id=lead.lead_id,
        from_email=lead.business_email,
        subject="Sample Request",
        raw_body="Please send samples to Hamburg.",
    )
    process_incoming_reply(req=req, db=db_session)

    # Filter by classification
    rfq_list = list_replies(classification="Samples", db=db_session)
    assert len(rfq_list) >= 1
    assert all(r.classification == "Samples" for r in rfq_list)
