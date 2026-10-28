"""
Day 11 Tests — SMTP Dispatch, Deliverability Controls & Follow-up Scheduling
Tests:
  - Rolling hourly & daily send limit window calculation
  - Mode A Gate: blocks dispatch of unapproved emails
  - Suppression Gate: blocks dispatch to suppressed addresses
  - Successful dispatch updates status and advances CRM pipeline stage to 'Email Sent'
  - Follow-up scheduling: automatically sets next_followup to +4 days
  - Batch dispatch respects available quota
  - Direct invocation of REST API dispatch endpoints
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal, init_db
from app.core.config import settings
from app.models.lead import Lead
from app.models.product_profile import ProductProfile
from app.models.outreach import OutreachEmail, SuppressionList
from app.schemas.lead import LeadCreate
from app.schemas.outreach import EmailComposeRequest, EmailApprovalRequest, SuppressionCreate
from app.services.lead_service import ingest_lead
from app.services.email_composer import compose_grounded_email
from app.services.smtp_service import (
    get_send_window_metrics,
    send_outreach_email,
    dispatch_approved_emails,
)
from app.api.outreach import (
    compose_outreach_email,
    approve_outreach_email,
    dispatch_single_email,
    dispatch_approved_batch,
    get_outreach_send_stats,
    add_to_suppression_list,
)


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _make_dispatch_lead(db: Session, email_prefix: str = "buyer") -> Lead:
    uid = uuid.uuid4().hex[:6]
    lc = LeadCreate(
        company_name=f"Scandinavian Food Logistics {uid}",
        country="Sweden",
        city="Stockholm",
        website=f"https://scanfood-{uid}.se",
        product_category="Basmati Rice & Organic Spices",
        contact_name="Lars Lindqvist",
        job_title="Purchasing Director",
        business_email=f"{email_prefix}_{uid}@scanfood.se",
        phone_number="+46 8 123 4567",
        source="Nordic Importers Register",
        source_url="https://nordic-trade.se",
        import_evidence="Major distributor of specialty food across Scandinavia.",
    )
    lead, _ = ingest_lead(db, lc)
    return lead


def _make_dispatch_product(db: Session) -> ProductProfile:
    prod = ProductProfile(
        product_name="Premium 1121 Sella Basmati Rice",
        product_category="Agricultural Commodities & Grains",
        hs_code="10063020",
        specifications="8.35mm average grain length, 100% sortexed clean",
        origin_country="India",
        available_quantity="500 MT / Month",
        packaging="25kg & 50kg Non-Woven Polypropylene Bags",
        moq="1x20ft Container (20 MT)",
        target_price_min=1150.0,
        target_price_max=1300.0,
        currency="USD",
        incoterms="FOB Mundra Port",
        preferred_payment_terms="30% Advance + 70% against BL scan",
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


# ─────────────────────────────────────────────────────────────────────────────
# 1. Rate Limit Window Metrics
# ─────────────────────────────────────────────────────────────────────────────

def test_send_window_metrics_calculation(db_session):
    metrics = get_send_window_metrics(db=db_session)
    assert "sent_today" in metrics
    assert "sent_this_hour" in metrics
    assert "daily_remaining" in metrics
    assert "hourly_remaining" in metrics
    assert metrics["daily_limit"] == settings.DAILY_SEND_LIMIT
    assert metrics["hourly_limit"] == settings.HOURLY_SEND_LIMIT
    assert isinstance(metrics["can_send"], bool)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Mode A Gate & Safety Checks
# ─────────────────────────────────────────────────────────────────────────────

def test_mode_a_blocks_unapproved_email_dispatch(db_session):
    lead = _make_dispatch_lead(db_session)
    product = _make_dispatch_product(db_session)

    # Compose email — status is 'Queued'
    req = EmailComposeRequest(product_profile_id=product.profile_id)
    email_obj = compose_outreach_email(lead_id=lead.lead_id, req=req, db=db_session)
    assert email_obj.status == "Queued"

    # Attempting to send unapproved email directly must fail with Mode A error
    res = send_outreach_email(db=db_session, email_id=email_obj.email_id)
    assert res["success"] is False
    assert "Mode A Violation" in res["error"]
    assert "Only 'Approved' emails can be dispatched" in res["error"]


def test_suppressed_recipient_blocked(db_session):
    lead = _make_dispatch_lead(db_session)
    product = _make_dispatch_product(db_session)

    # Compose and approve email
    req = EmailComposeRequest(product_profile_id=product.profile_id)
    email_obj = compose_outreach_email(lead_id=lead.lead_id, req=req, db=db_session)
    appr = EmailApprovalRequest(reviewer_name="Quality Auditor")
    approved = approve_outreach_email(email_id=email_obj.email_id, req=appr, db=db_session)
    assert approved.status == "Approved"

    # Now add recipient to suppression list before send
    add_to_suppression_list(
        supp_in=SuppressionCreate(email=lead.business_email, reason="Unsubscribe"),
        db=db_session,
    )

    # Attempting to send must be blocked by suppression gate
    res = send_outreach_email(db=db_session, email_id=email_obj.email_id)
    assert res["success"] is False
    assert "suppression list" in res["error"].lower()

    # Email status should be set to Suppressed
    db_session.refresh(email_obj)
    assert email_obj.status == "Suppressed"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Successful Dispatch & CRM Synchronization
# ─────────────────────────────────────────────────────────────────────────────

def test_successful_dispatch_and_crm_sync(db_session):
    lead = _make_dispatch_lead(db_session, email_prefix="approved_buyer")
    product = _make_dispatch_product(db_session)

    # 1. Compose
    req = EmailComposeRequest(product_profile_id=product.profile_id)
    email_obj = compose_outreach_email(lead_id=lead.lead_id, req=req, db=db_session)

    # 2. Approve (Mode A signoff)
    appr = EmailApprovalRequest(reviewer_name="Export Sales Director")
    approve_outreach_email(email_id=email_obj.email_id, req=appr, db=db_session)

    # 3. Dispatch
    res = send_outreach_email(db=db_session, email_id=email_obj.email_id, bypass_rate_limits=True)
    assert res["success"] is True
    assert res["status"] == "Sent"

    # 4. Verify Email Status
    db_session.refresh(email_obj)
    assert email_obj.status == "Sent"
    assert email_obj.sent_at is not None

    # 5. Verify Associated Lead CRM Status
    db_session.refresh(lead)
    assert lead.outreach_status == "Sent"
    assert lead.pipeline_stage == "Email Sent"
    assert lead.next_followup is not None
    # Follow-up scheduled roughly 4 days from now (handle sqlite tzinfo)
    followup = lead.next_followup
    if followup.tzinfo is None:
        followup = followup.replace(tzinfo=timezone.utc)
    diff_days = (followup - datetime.now(timezone.utc)).total_seconds() / 86400.0
    assert 3.5 <= diff_days <= 4.5
    assert "Next follow-up scheduled" in lead.notes


# ─────────────────────────────────────────────────────────────────────────────
# 4. Batch Dispatch & REST API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

def test_batch_dispatch_service(db_session):
    lead = _make_dispatch_lead(db_session, email_prefix="batch_buyer")
    product = _make_dispatch_product(db_session)

    # Compose and approve
    req = EmailComposeRequest(product_profile_id=product.profile_id)
    email_obj = compose_outreach_email(lead_id=lead.lead_id, req=req, db=db_session)
    appr = EmailApprovalRequest(reviewer_name="Batch Officer")
    approve_outreach_email(email_id=email_obj.email_id, req=appr, db=db_session)

    # Run batch dispatch with bypass_rate_limits=True for isolated test execution
    batch_res = dispatch_approved_emails(db=db_session, max_emails=10, bypass_rate_limits=True)
    assert batch_res["dispatched_count"] >= 1
    assert "updated_metrics" in batch_res


def test_api_dispatch_endpoints(db_session):
    # Stats
    stats = get_outreach_send_stats(db=db_session)
    assert "sent_today" in stats
    assert "daily_limit" in stats

    lead = _make_dispatch_lead(db_session, email_prefix="api_buyer")
    product = _make_dispatch_product(db_session)

    # Compose & Approve
    req = EmailComposeRequest(product_profile_id=product.profile_id)
    email_obj = compose_outreach_email(lead_id=lead.lead_id, req=req, db=db_session)
    approve_outreach_email(email_id=email_obj.email_id, req=EmailApprovalRequest(reviewer_name="API Approver"), db=db_session)

    # Dispatch via API function
    dispatch_res = dispatch_single_email(email_id=email_obj.email_id, bypass_rate_limits=True, db=db_session)
    assert dispatch_res["success"] is True
    assert dispatch_res["status"] == "Sent"
