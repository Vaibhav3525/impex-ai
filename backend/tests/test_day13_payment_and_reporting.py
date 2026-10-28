"""
Day 13 — Transaction Financial Safety & Executive KPI Reporting Tests
Validates deal-level commercial risk assessment, exposure management,
and PRD §5 10-metric executive performance reporting.
"""

import uuid
import pytest
from app.core.database import SessionLocal
from app.models.lead import Lead
from app.models.deal import Deal, BuyerReply
from app.models.outreach import OutreachEmail
from app.services.payment_risk import assess_deal_financial_risk, audit_and_save_deal_risk
from app.api.pipeline import evaluate_and_audit_deal_financial_risk, get_deal_financial_risk
from app.api.analytics import get_executive_report, export_leads_csv


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_assess_deal_high_risk_open_account(db_session):
    """Open Account terms for unverified buyer must be blocked with high risk."""
    uid = uuid.uuid4().hex[:6]
    lead = Lead(
        lead_id=f"LEAD-RISK-{uid}",
        company_name=f"Risky Importer {uid}",
        country="Nigeria",
        verification_status="Unverified",
        payment_risk_score=65.0,
        risk_level="HIGH",
        risk_flags=["FLAG_FREE_EMAIL_DOMAIN"]
    )
    deal = Deal(
        deal_id=f"DEAL-RISK-{uid}",
        lead_id=lead.lead_id,
        product_name="Basmati Rice",
        payment_terms="Open Account 60 Days",
        quotation_amount=45000.0,
        stage="Negotiation"
    )

    assessment = assess_deal_financial_risk(deal, lead)
    assert assessment["status"] == "Blocked"
    assert assessment["risk_rating"] == "HIGH"
    assert assessment["human_approval_required"] is True
    assert any("Unsecured payment structure" in f for f in assessment["risk_factors"])


def test_assess_deal_critical_fraud_pattern_blocked(db_session):
    """Buyer with critical scam flags must trigger instant execution block."""
    uid = uuid.uuid4().hex[:6]
    lead = Lead(
        lead_id=f"LEAD-SCAM-{uid}",
        company_name=f"Fraudulent Buyer {uid}",
        country="Togo",
        verification_status="Rejected",
        payment_risk_score=95.0,
        risk_level="CRITICAL",
        risk_flags=["FLAG_ADVANCE_FEE_SCAM"]
    )
    deal = Deal(
        deal_id=f"DEAL-SCAM-{uid}",
        lead_id=lead.lead_id,
        product_name="Organic Spices",
        payment_terms="100% Advance Wire", # Even with advance wire, scam identity halts transaction
        quotation_amount=15000.0,
        stage="Requirements Received"
    )

    assessment = assess_deal_financial_risk(deal, lead)
    assert assessment["status"] == "Blocked"
    assert assessment["risk_rating"] == "CRITICAL"
    assert assessment["human_approval_required"] is True
    assert "DO NOT SHIP" in assessment["recommended_action"]


def test_assess_deal_secure_advance_terms_approved(db_session):
    """100% advance wire for low-risk buyer is safely approved."""
    uid = uuid.uuid4().hex[:6]
    lead = Lead(
        lead_id=f"LEAD-SECURE-{uid}",
        company_name=f"Reputable Importer {uid}",
        country="Germany",
        verification_status="Verified",
        payment_risk_score=5.0,
        risk_level="LOW",
        risk_flags=[]
    )
    deal = Deal(
        deal_id=f"DEAL-SECURE-{uid}",
        lead_id=lead.lead_id,
        product_name="Black Pepper",
        payment_terms="100% Advance Wire",
        quotation_amount=25000.0,
        stage="Negotiation"
    )

    assessment = assess_deal_financial_risk(deal, lead)
    assert assessment["status"] == "Approved"
    assert assessment["risk_rating"] == "LOW"
    assert assessment["human_approval_required"] is False


def test_assess_deal_large_capital_exposure_triggers_management_review(db_session):
    """Deals over USD 100,000 enforce management approval even under standard LC."""
    uid = uuid.uuid4().hex[:6]
    lead = Lead(
        lead_id=f"LEAD-LARGE-{uid}",
        company_name=f"Global Foods Corp {uid}",
        country="United States",
        verification_status="Verified",
        payment_risk_score=10.0,
        risk_level="LOW",
        risk_flags=[]
    )
    deal = Deal(
        deal_id=f"DEAL-LARGE-{uid}",
        lead_id=lead.lead_id,
        product_name="Processed Mango Pulp",
        payment_terms="Irrevocable LC at Sight",
        quotation_amount=250000.0, # Large exposure
        stage="Quotation Prepared"
    )

    assessment = assess_deal_financial_risk(deal, lead)
    assert any("Large capital exposure" in f for f in assessment["risk_factors"])
    assert assessment["human_approval_required"] is True


def test_audit_and_save_deal_risk_persists(db_session):
    """Assessing and saving deal financial risk updates the deal in database."""
    uid = uuid.uuid4().hex[:6]
    lead = Lead(
        lead_id=f"LEAD-DB-{uid}",
        company_name=f"Dubai Foodstuffs LLC {uid}",
        country="United Arab Emirates",
        product_category="Cardamom Extra Bold",
        source="APEDA Directory",
        dedup_hash=f"hash_{uid}",
        verification_status="Verified",
        payment_risk_score=15.0,
        risk_level="LOW",
        risk_flags=[]
    )
    db_session.add(lead)
    db_session.commit()

    deal = Deal(
        deal_id=f"DEAL-DB-{uid}",
        lead_id=lead.lead_id,
        product_name="Cardamom Extra Bold",
        payment_terms="Documents Against Acceptance 90 Days",
        quotation_amount=80000.0,
        stage="Negotiation"
    )
    db_session.add(deal)
    db_session.commit()

    assessment = audit_and_save_deal_risk(db_session, deal, lead)
    assert assessment["status"] == "Blocked"

    # Query afresh from DB
    reloaded = db_session.query(Deal).filter(Deal.deal_id == deal.deal_id).first()
    assert reloaded.payment_risk_status == "Blocked"
    assert "HIGH RISK" in reloaded.payment_risk_notes


def test_deal_financial_risk_api_endpoints(db_session):
    """Test POST and GET /deals/{id}/financial-risk API endpoints."""
    uid = uuid.uuid4().hex[:6]
    lead = Lead(
        lead_id=f"LEAD-API-{uid}",
        company_name=f"Tokyo Trading KK {uid}",
        country="Japan",
        product_category="Turmeric Powder",
        source="Indian Trade Portal",
        dedup_hash=f"hash_{uid}",
        verification_status="Verified",
        payment_risk_score=8.0,
        risk_level="LOW",
        risk_flags=[]
    )
    db_session.add(lead)
    db_session.commit()

    deal = Deal(
        deal_id=f"DEAL-API-{uid}",
        lead_id=lead.lead_id,
        product_name="Turmeric Powder",
        payment_terms="Confirmed Irrevocable LC",
        quotation_amount=50000.0,
        stage="Purchase Order Received"
    )
    db_session.add(deal)
    db_session.commit()

    # Call POST API
    post_res = evaluate_and_audit_deal_financial_risk(deal.deal_id, db=db_session)
    assert post_res.deal_id == deal.deal_id
    assert post_res.status == "Approved"
    assert post_res.risk_rating == "LOW"

    # Call GET API
    get_res = get_deal_financial_risk(deal.deal_id, db=db_session)
    assert get_res.deal_id == deal.deal_id
    assert get_res.status == "Approved"


def test_executive_report_aggregates_ten_prd_metrics(db_session):
    """Validates the 10 PRD §5 metrics, revenue accounting, and source yield."""
    uid = uuid.uuid4().hex[:6]
    lead = Lead(
        lead_id=f"LEAD-EXEC-{uid}",
        company_name=f"Executive Importer {uid}",
        country="United Kingdom",
        product_category="Sesame Seeds",
        source="APEDA Directory",
        dedup_hash=f"hash_{uid}",
        verification_status="Verified",
        buyer_score=88.0,
        business_email=f"procure_{uid}@execimport.co.uk",
        pipeline_stage="Order Confirmed"
    )
    db_session.add(lead)
    db_session.commit()

    # Outreach Email
    email = OutreachEmail(
        email_id=f"EML-EXEC-{uid}",
        lead_id=lead.lead_id,
        to_email=lead.business_email,
        company_name=lead.company_name,
        country="United Kingdom",
        subject="Export Quotation",
        body_text="Here is the price specification.",
        status="Delivered"
    )
    db_session.add(email)

    # Buyer Reply
    reply = BuyerReply(
        lead_id=lead.lead_id,
        from_email=lead.business_email,
        subject="Re: Export Quotation",
        raw_body="We accept the terms. Please issue proforma invoice.",
        classification="Interested Buyer",
        confidence_score=0.95
    )
    db_session.add(reply)

    # Confirmed Deal
    deal = Deal(
        deal_id=f"DEAL-EXEC-{uid}",
        lead_id=lead.lead_id,
        product_name="Sesame Seeds",
        stage="Order Confirmed",
        quotation_amount=70000.0,
        confirmed_order_value=68500.0
    )
    db_session.add(deal)
    db_session.commit()

    report = get_executive_report(db=db_session)
    
    # Check 10 metrics presence and counts
    m = report["prd_10_core_metrics"]
    assert m["1_raw_records_discovered"] > 0
    assert m["2_unique_companies_identified"] > 0
    assert m["3_companies_successfully_verified"] > 0
    assert m["4_qualified_potential_buyers"] > 0
    assert m["5_valid_business_email_addresses"] > 0
    assert m["6_emails_approved_for_outreach"] > 0
    assert m["7_emails_successfully_delivered"] > 0
    assert m["8_replies_received"] > 0
    assert m["9_qualified_buyer_inquiries"] > 0
    assert m["10_quotations_and_orders"] > 0

    # Financial verification
    fin = report["financial_performance"]
    assert fin["confirmed_realized_revenue_usd"] >= 68500.0
    assert fin["total_quotations_value_usd"] >= 70000.0

    # Source yield
    assert isinstance(report["source_yield_breakdown"], list)
    assert any(s["source"] == "APEDA Directory" for s in report["source_yield_breakdown"])

    # Disclaimers
    assert "No guaranteed buyers" in report["compliance_disclaimer"]


def test_export_leads_csv_endpoint(db_session):
    """PRD §13 & §14: Export verified leads to CSV for DGFT/APEDA audit compliance."""
    res = export_leads_csv(db=db_session)
    assert res.media_type == "text/csv"
    assert "impex_verified_buyers_audit.csv" in res.headers["Content-Disposition"]

    content = res.body
    text = content.decode() if isinstance(content, bytes) else str(content)
    assert "Lead ID,Company Name,Country" in text
    assert "Buyer Score (/100)" in text
    assert "Provenance Source" in text

