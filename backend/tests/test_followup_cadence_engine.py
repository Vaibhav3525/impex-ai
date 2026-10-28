"""
Test Suite: PRD §7 & §12 Autonomous Follow-Up Cadence Engine & Reply Auto-Halting
Verifies:
  1. Sequence 1 -> Sequence 2 (Day 4) -> Sequence 3 (Day 8) cadence progression.
  2. Cadence interval enforcement (4-day delay) & force override.
  3. Strict hard cap of exactly 3 touches (no Touch 4 allowed).
  4. Instant auto-halt and cancellation of pending follow-ups upon incoming reply.
  5. Automatic suppression and opt-out handling for "Not Interested" replies.
  6. Pipeline funnel reporting and bulk follow-up processing.
"""

import uuid
import hashlib
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.models.product_profile import ProductProfile
from app.models.outreach import OutreachEmail, SuppressionList
from app.models.deal import BuyerReply
from app.schemas.reply import IncomingReplyRequest
from app.schemas.outreach import FollowupProcessRequest
from app.services.followup_service import (
    is_lead_eligible_for_followup,
    generate_next_followup_email,
    cancel_pending_followups_for_lead,
    process_all_due_followups,
    get_cadence_pipeline_status,
)
from app.api.replies import process_incoming_reply
from app.api.outreach import (
    get_cadence_status,
    process_due_followups_endpoint,
    schedule_lead_next_followup,
    cancel_lead_followups,
)


@pytest.fixture
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _make_lead(db: Session, prefix: str = "cadence") -> Lead:
    uid = uuid.uuid4().hex[:6]
    company = f"Al Maya Logistics {uid}"
    email = f"{prefix}_{uid}@almaya.ae"
    h = hashlib.sha256(f"{company.lower()}_{email}".encode()).hexdigest()

    lead = Lead(
        lead_id=f"LEAD-CAD-{uid.upper()}",
        company_name=company,
        country="United Arab Emirates",
        city="Dubai",
        product_category="Basmati Rice",
        business_email=email,
        contact_name="Mr. Kamal Vachani",
        job_title="Director of Procurement",
        buyer_score=85.0,
        verification_status="Verified",
        source="Indian Trade Portal",
        pipeline_stage="Email Sent",
        outreach_status="Contacted",
        dedup_hash=h,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def _make_product(db: Session) -> ProductProfile:
    uid = uuid.uuid4().hex[:6]
    prod = ProductProfile(
        profile_id=f"PROD-RICE-{uid.upper()}",
        product_name="1121 Traditional Basmati Rice",
        product_category="Agricultural Commodities & Grains",
        hs_code="10063020",
        origin_country="India",
        certifications=["APEDA", "FSSAI", "ISO 22000"],
        grade="Premium Aged 2 Years",
        specifications="Average grain length 8.35mm, Moisture max 12%",
        packaging="25kg Master Polypropylene Bags",
        incoterms="CIF Jebel Ali",
        preferred_payment_terms="100% Irrevocable LC at Sight",
        target_price_min=1100.0,
        target_price_max=1250.0,
        currency="USD",
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


# ─────────────────────────────────────────────────────────────────────────────
# 1. Eligibility Checks
# ─────────────────────────────────────────────────────────────────────────────

def test_followup_eligibility_rules(db_session):
    lead = _make_lead(db_session, "elig")
    prod = _make_product(db_session)

    # Rule 1: Cannot follow up if Touch 1 hasn't been sent yet
    eligible, reason = is_lead_eligible_for_followup(lead, db_session)
    assert not eligible
    assert "not been sent yet" in reason

    # Send Touch 1
    touch_1 = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country=lead.country,
        subject="Export Inquiry: Basmati Rice",
        body_text="Introductory text...",
        sequence_step=1,
        status="Sent",
        sent_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    db_session.add(touch_1)
    db_session.commit()

    # Rule 2: Now eligible
    eligible, reason = is_lead_eligible_for_followup(lead, db_session)
    assert eligible
    assert reason == "Eligible"

    # Rule 3: Ineligible if pending email is already in queue
    touch_2_queued = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country=lead.country,
        subject="Follow-up: Basmati Rice",
        body_text="Follow-up text...",
        sequence_step=2,
        status="Queued",
    )
    db_session.add(touch_2_queued)
    db_session.commit()

    eligible, reason = is_lead_eligible_for_followup(lead, db_session)
    assert not eligible
    assert "already" in reason

    # Clean up
    db_session.delete(touch_2_queued)
    db_session.commit()

    # Rule 4: Ineligible if lead status is "Replied"
    lead.outreach_status = "Replied"
    db_session.commit()
    eligible, reason = is_lead_eligible_for_followup(lead, db_session)
    assert not eligible
    assert "Replied" in reason

    # Reset
    lead.outreach_status = "Contacted"
    db_session.commit()

    # Rule 5: Ineligible if lead is suppressed
    supp = SuppressionList(email=lead.business_email.lower(), reason="Unsubscribe")
    db_session.add(supp)
    db_session.commit()

    eligible, reason = is_lead_eligible_for_followup(lead, db_session)
    assert not eligible
    assert "suppression list" in reason


# ─────────────────────────────────────────────────────────────────────────────
# 2. Sequence 1 -> Sequence 2 (Day 4) Generation & Interval Enforcement
# ─────────────────────────────────────────────────────────────────────────────

def test_sequence_2_generation_and_interval_enforcement(db_session):
    lead = _make_lead(db_session, "seq2")
    prod = _make_product(db_session)

    # Touch 1 sent only 1 day ago (not yet due for 4-day cadence)
    touch_1 = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country=lead.country,
        subject="Introductory note",
        body_text="Introductory text",
        sequence_step=1,
        status="Sent",
        sent_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(touch_1)
    db_session.commit()

    # Attempt to generate next without force: should return None
    next_email = generate_next_followup_email(db_session, lead.lead_id, min_days=4, force=False)
    assert next_email is None

    # Attempt with force=True: successfully generates Touch 2
    touch_2 = generate_next_followup_email(db_session, lead.lead_id, min_days=4, force=True)
    assert touch_2 is not None
    assert touch_2.sequence_step == 2
    assert "Follow-up" in touch_2.subject
    assert "1121 Traditional Basmati Rice" in touch_2.subject
    assert "samples" in touch_2.body_text.lower()
    assert touch_2.status == "Queued"
    assert touch_2.scheduled_for is not None
    assert "Follow-up 2 Queued" in lead.outreach_status


# ─────────────────────────────────────────────────────────────────────────────
# 3. Sequence 2 -> Sequence 3 (Day 8) Generation
# ─────────────────────────────────────────────────────────────────────────────

def test_sequence_3_generation(db_session):
    lead = _make_lead(db_session, "seq3")
    prod = _make_product(db_session)

    # Touch 1 and Touch 2 already sent
    touch_1 = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country=lead.country,
        subject="Introductory note",
        body_text="Intro",
        sequence_step=1,
        status="Sent",
        sent_at=datetime.now(timezone.utc) - timedelta(days=9),
    )
    touch_2 = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country=lead.country,
        subject="Follow-up note",
        body_text="Follow-up",
        sequence_step=2,
        status="Sent",
        sent_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    db_session.add_all([touch_1, touch_2])
    db_session.commit()

    # Generate Touch 3
    touch_3 = generate_next_followup_email(db_session, lead.lead_id, min_days=4, force=False)
    assert touch_3 is not None
    assert touch_3.sequence_step == 3
    assert "Final Inquiry" in touch_3.subject
    assert "harvest cycles" in touch_3.body_text.lower() or "specifications on file" in touch_3.body_text.lower()
    assert touch_3.status == "Queued"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Strict Hard Cap at 3 Touches
# ─────────────────────────────────────────────────────────────────────────────

def test_hard_cap_at_3_touches(db_session):
    lead = _make_lead(db_session, "cap3")
    prod = _make_product(db_session)

    # All 3 touches sent
    for step in range(1, 4):
        em = OutreachEmail(
            lead_id=lead.lead_id,
            product_id=prod.profile_id,
            to_email=lead.business_email,
            company_name=lead.company_name,
            country=lead.country,
            subject=f"Touch {step}",
            body_text=f"Body {step}",
            sequence_step=step,
            status="Sent",
            sent_at=datetime.now(timezone.utc) - timedelta(days=12 - step * 3),
        )
        db_session.add(em)
    db_session.commit()

    # Eligibility must be False
    eligible, reason = is_lead_eligible_for_followup(lead, db_session)
    assert not eligible
    assert "Max cadence limit reached" in reason

    # Attempt to generate touch 4 returns None
    touch_4 = generate_next_followup_email(db_session, lead.lead_id, force=True)
    assert touch_4 is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Inbound Reply Auto-Halts Cadence
# ─────────────────────────────────────────────────────────────────────────────

def test_inbound_reply_auto_halts_cadence(db_session):
    lead = _make_lead(db_session, "halt")
    prod = _make_product(db_session)

    # Touch 1 sent
    touch_1 = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country=lead.country,
        subject="Introductory",
        body_text="Body",
        sequence_step=1,
        status="Sent",
        sent_at=datetime.now(timezone.utc) - timedelta(days=4),
    )
    # Touch 2 queued for approval
    touch_2 = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country=lead.country,
        subject="Follow-up",
        body_text="Body",
        sequence_step=2,
        status="Queued",
    )
    db_session.add_all([touch_1, touch_2])
    db_session.commit()

    # Buyer responds with RFQ
    reply_req = IncomingReplyRequest(
        lead_id=lead.lead_id,
        from_email=lead.business_email,
        subject="Re: Export Inquiry: Basmati Rice",
        raw_body="Thank you for reaching out. Please send CIF quotation for 500 MT of 1121 Basmati Rice to Jebel Ali port. LC at sight.",
    )

    reply_res = process_incoming_reply(req=reply_req, db=db_session)
    assert reply_res.classification == "Request for Quotation"
    assert reply_res.extracted_delivery_port == "Jebel Ali"

    # Verify Touch 2 was automatically cancelled / suppressed
    db_session.refresh(touch_2)
    assert touch_2.status == "Suppressed"
    assert "Cadence Auto-Halted" in touch_2.rejection_reason

    # Verify lead pipeline progressed
    db_session.refresh(lead)
    assert lead.outreach_status == "Replied"
    assert lead.pipeline_stage == "Requirements Received"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Unsubscribe / Not Interested Auto-Suppression
# ─────────────────────────────────────────────────────────────────────────────

def test_unsubscribe_auto_suppresses_cadence(db_session):
    lead = _make_lead(db_session, "optout")
    prod = _make_product(db_session)

    touch_1 = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country=lead.country,
        subject="Intro",
        body_text="Body",
        sequence_step=1,
        status="Sent",
        sent_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    touch_2 = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country=lead.country,
        subject="Follow-up",
        body_text="Body",
        sequence_step=2,
        status="Approved",
    )
    db_session.add_all([touch_1, touch_2])
    db_session.commit()

    # Buyer responds with opt-out
    reply_req = IncomingReplyRequest(
        lead_id=lead.lead_id,
        from_email=lead.business_email,
        subject="Unsubscribe",
        raw_body="Please remove us from your mailing list, we are not interested at this time.",
    )

    reply_res = process_incoming_reply(req=reply_req, db=db_session)
    assert reply_res.classification == "Not Interested"

    # Check lead status
    db_session.refresh(lead)
    assert lead.outreach_status == "Opted-Out"

    # Check suppression registry
    supp = db_session.query(SuppressionList).filter(SuppressionList.email == lead.business_email.lower()).first()
    assert supp is not None
    assert supp.reason == "Unsubscribe"

    # Check touch 2 was cancelled
    db_session.refresh(touch_2)
    assert touch_2.status == "Suppressed"
    assert "Cadence Auto-Halted" in touch_2.rejection_reason


# ─────────────────────────────────────────────────────────────────────────────
# 7. Follow-Up REST API Endpoints & Bulk Processing
# ─────────────────────────────────────────────────────────────────────────────

def test_followup_api_endpoints(db_session):
    lead = _make_lead(db_session, "api")
    prod = _make_product(db_session)

    touch_1 = OutreachEmail(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country=lead.country,
        subject="German Intro",
        body_text="Body text",
        sequence_step=1,
        status="Sent",
        sent_at=datetime.now(timezone.utc) - timedelta(days=6),
    )
    db_session.add(touch_1)
    db_session.commit()

    # Test get_cadence_status
    status_data = get_cadence_status(db=db_session)
    assert status_data["touch_1_sent"] >= 1

    # Test process_due_followups_endpoint (batch run)
    proc_req = FollowupProcessRequest(
        min_days=4,
        force_advance=False,
        limit=50,
    )
    batch_res = process_due_followups_endpoint(req=proc_req, db=db_session)
    assert batch_res.generated_count >= 1
    assert any(e.lead_id == lead.lead_id and e.sequence_step == 2 for e in batch_res.generated_emails)

    # Test cancel_lead_followups
    cancel_data = cancel_lead_followups(lead_id=lead.lead_id, reason="Manual Stop", db=db_session)
    assert cancel_data["status"] == "Halted"
    assert cancel_data["cancelled_count"] >= 1
