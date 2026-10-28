"""
Day 8 Tests — Payment Risk Guardian & Fraud Detection Engine
Tests:
  - Advance fee scam keyword detection (CRITICAL severity)
  - Third-party offshore payment diversion detection (HIGH severity)
  - Free webmail risk flag
  - Country vs ccTLD domain mismatch detection
  - Clean buyer low-risk rating
  - Strict separation invariant: Qualification Score != Payment Risk Score
  - Persistence of payment_risk_score and risk_level in database
  - High-risk monitoring queue API
  - Risk assessment REST endpoints
"""

import uuid
import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.schemas.lead import LeadCreate
from app.services.lead_service import ingest_lead
from app.services.risk_service import (
    evaluate_lead_payment_risk,
    audit_and_save_lead_risk,
    check_country_tld_mismatch,
)
from app.api.leads import (
    get_high_risk_leads,
    evaluate_and_persist_risk,
    get_lead_risk_assessment,
)


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _make_risk_lead(db: Session, **kwargs) -> Lead:
    uid = uuid.uuid4().hex[:6]
    defaults = {
        "company_name": f"International Traders Ltd {uid}",
        "country": "Germany",
        "city": "Frankfurt",
        "website": f"https://int-traders-{uid}.de",
        "product_category": "Spices & Food Commodities",
        "contact_name": "Klaus Richter",
        "job_title": "Head of Sourcing",
        "business_email": f"klaus@{uid}-traders.de",
        "phone_number": "+49 69 123456",
        "source": "German Trade Registry",
        "source_url": "https://handelsregister.de",
        "import_evidence": "Documented importer of food ingredients.",
    }
    defaults.update(kwargs)
    lc = LeadCreate(**defaults)
    lead, _ = ingest_lead(db, lc)
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# 1. Advance Fee Scam Detection (CRITICAL)
# ─────────────────────────────────────────────────────────────────────────────

def test_advance_fee_scam_pattern_detected(db_session):
    lead = _make_risk_lead(
        db_session,
        notes="Buyer requires supplier to pay a tender registration fee upfront before contract issuance.",
    )
    assessment = evaluate_lead_payment_risk(lead)

    assert assessment.risk_level == "CRITICAL"
    assert assessment.payment_risk_score >= 40.0
    assert assessment.requires_human_approval is True
    assert assessment.is_safe_for_automated_outreach is False
    assert any(s.flag == "FLAG_ADVANCE_FEE_SCAM" for s in assessment.detected_signals)
    assert any("registration fee" in s.evidence.lower() for s in assessment.detected_signals)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Third-Party Payer Diversion (HIGH)
# ─────────────────────────────────────────────────────────────────────────────

def test_third_party_payment_diversion_detected(db_session):
    lead = _make_risk_lead(
        db_session,
        notes="Buyer states that an alternate company paying from a different country bank will wire funds.",
    )
    assessment = evaluate_lead_payment_risk(lead)

    assert assessment.risk_level in ("HIGH", "CRITICAL")
    assert assessment.payment_risk_score >= 25.0
    assert assessment.requires_human_approval is True
    assert any(s.flag == "FLAG_THIRD_PARTY_PAYER" for s in assessment.detected_signals)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Free Webmail Domain Risk
# ─────────────────────────────────────────────────────────────────────────────

def test_free_email_domain_flag(db_session):
    lead = _make_risk_lead(
        db_session,
        business_email="global_buyer_agent@gmail.com",
    )
    assessment = evaluate_lead_payment_risk(lead)

    assert any(s.flag == "FLAG_FREE_EMAIL_DOMAIN" for s in assessment.detected_signals)
    assert assessment.payment_risk_score >= 25.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Country vs ccTLD Inconsistency
# ─────────────────────────────────────────────────────────────────────────────

def test_country_tld_mismatch_detected(db_session):
    # Stated country is United States, but website uses German ccTLD (.de)
    lead = _make_risk_lead(
        db_session,
        country="United States",
        website="https://www.usgrain-procurement.de",
    )
    assessment = evaluate_lead_payment_risk(lead)

    assert any(s.flag == "FLAG_COUNTRY_MISMATCH" for s in assessment.detected_signals)
    assert assessment.payment_risk_score >= 20.0


def test_country_tld_matching_no_flag(db_session):
    # German buyer with .de website — should NOT trigger mismatch
    res = check_country_tld_mismatch("https://acme.de", "Germany")
    assert res is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Clean Buyer Low-Risk Profile
# ─────────────────────────────────────────────────────────────────────────────

def test_clean_buyer_low_risk(db_session):
    lead = _make_risk_lead(
        db_session,
        country="Norway",
        website="https://nordicfish.no",
        business_email="purchasing@nordicfish.no",
        import_evidence="Verified regular importer of Indian spices with confirmed customs records.",
        notes="Standard 30% advance + 70% against BL terms requested.",
    )
    assessment = evaluate_lead_payment_risk(lead)

    assert assessment.risk_level == "LOW"
    assert assessment.payment_risk_score < 20.0
    assert assessment.requires_human_approval is False
    assert assessment.is_safe_for_automated_outreach is True
    assert "LOW RISK" in assessment.summary


# ─────────────────────────────────────────────────────────────────────────────
# 6. Strict Separation Invariant (PRD §4 & §11)
# ─────────────────────────────────────────────────────────────────────────────

def test_qualification_score_does_not_cancel_payment_risk(db_session):
    """
    PRD Invariant:
    A company may receive a high relevance score while still having unresolved payment or identity risks.
    The system must maintain separate qualification and risk indicators.
    """
    lead = _make_risk_lead(
        db_session,
        product_category="Organic Basmati Rice",
        notes="High volume buyer but insists on supplier paying legal registration fee upfront.",
    )
    # Set high buyer score to simulate highly qualified commodity match
    lead.buyer_score = 92.0
    db_session.commit()
    db_session.refresh(lead)

    assessment = evaluate_lead_payment_risk(lead)

    # High buyer score is preserved
    assert assessment.buyer_score == 92.0
    # Payment risk is still CRITICAL despite high buyer score
    assert assessment.risk_level == "CRITICAL"
    assert assessment.payment_risk_score >= 40.0
    assert assessment.is_safe_for_automated_outreach is False


# ─────────────────────────────────────────────────────────────────────────────
# 7. Persistence & Database Verification
# ─────────────────────────────────────────────────────────────────────────────

def test_audit_and_save_lead_risk_persists(db_session):
    lead = _make_risk_lead(
        db_session,
        notes="Tender fee must be paid before procurement board will review quotation.",
    )
    assessment = audit_and_save_lead_risk(db_session, lead)

    db_session.refresh(lead)
    assert lead.payment_risk_score == assessment.payment_risk_score
    assert lead.risk_level == assessment.risk_level
    assert "FLAG_ADVANCE_FEE_SCAM" in lead.risk_flags


# ─────────────────────────────────────────────────────────────────────────────
# 8. High-Risk Monitoring Queue & API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

def test_high_risk_queue_api(db_session):
    lead = _make_risk_lead(
        db_session,
        notes="Offshore payment from another jurisdiction through unregulated third party agent.",
    )
    audit_and_save_lead_risk(db_session, lead)

    high_risk_list = get_high_risk_leads(limit=50, db=db_session)
    assert len(high_risk_list) >= 1
    high_risk_ids = [l.lead_id for l in high_risk_list]
    assert lead.lead_id in high_risk_ids


def test_api_risk_assessment_endpoints(db_session):
    lead = _make_risk_lead(db_session)
    
    # POST endpoint: evaluates and saves
    persisted = evaluate_and_persist_risk(lead_id=lead.lead_id, db=db_session)
    assert persisted.lead_id == lead.lead_id
    assert persisted.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    # GET endpoint: evaluates on the fly
    retrieved = get_lead_risk_assessment(lead_id=lead.lead_id, db=db_session)
    assert retrieved.lead_id == lead.lead_id
    assert retrieved.payment_risk_score == persisted.payment_risk_score
