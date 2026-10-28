"""
Day 7 Tests — Full 100-Point Verification Engine & Batch/Manual Auditing
Tests:
  - Batch verification endpoint (high-throughput processing)
  - Manual review queue filtering for uncertain and flagged cases
  - Human reviewer override with audit justification
  - Tamper-evident VerificationLog audit trail
  - Pipeline progression on verification upgrade
  - Input validation on status overrides
"""

import uuid
import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.models.verification import VerificationLog
from app.schemas.lead import (
    LeadCreate,
    BatchVerifyRequest,
    ManualVerificationRequest,
)
from app.services.lead_service import ingest_lead
from app.api.leads import (
    get_manual_review_queue,
    verify_batch_leads,
    manual_lead_verification_override,
    get_lead_audit_trail,
    trigger_verification,
)


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _make_test_lead(db: Session, status: str = "Unverified", flags: list = None, **kwargs) -> Lead:
    uid = uuid.uuid4().hex[:6]
    defaults = {
        "company_name": f"Nordic Import AS {uid}",
        "country": "Denmark",
        "city": "Copenhagen",
        "website": f"https://nordic-{uid}.dk",
        "product_category": "Spices & Organic Food",
        "contact_name": "Morten Jensen",
        "job_title": "Import Director",
        "business_email": f"morten@{uid}-nordic.dk",
        "phone_number": "+45 33 12 34 56",
        "source": "APEDA Buyer Directory",
        "source_url": "https://apeda.gov.in/",
        "import_evidence": "Documented importer of organic commodities into Scandinavia.",
    }
    defaults.update(kwargs)
    lc = LeadCreate(**defaults)
    lead, _ = ingest_lead(db, lc)
    lead.verification_status = status
    lead.risk_flags = flags or []
    db.commit()
    db.refresh(lead)
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# 1. Manual Review Queue
# ─────────────────────────────────────────────────────────────────────────────

def test_manual_review_queue_retrieval(db_session):
    # Create leads with different states
    partially_verified = _make_test_lead(db_session, status="Partially Verified", notes="Needs manual review")
    flagged_lead = _make_test_lead(db_session, status="Unverified", flags=["FLAG_FREE_EMAIL_DOMAIN"])

    queue = get_manual_review_queue(limit=50, db=db_session)
    assert len(queue) >= 2
    queue_ids = [l.lead_id for l in queue]
    assert partially_verified.lead_id in queue_ids
    assert flagged_lead.lead_id in queue_ids


# ─────────────────────────────────────────────────────────────────────────────
# 2. Batch Verification Engine
# ─────────────────────────────────────────────────────────────────────────────

def test_batch_verification_processing(db_session):
    # Create 3 unverified leads
    lead1 = _make_test_lead(db_session, status="Unverified", buyer_score=0.0)
    lead2 = _make_test_lead(db_session, status="Unverified", buyer_score=0.0)
    lead3 = _make_test_lead(db_session, status="Unverified", buyer_score=0.0)

    # Use sufficiently high limit to process all pending unverified leads
    req = BatchVerifyRequest(limit=100, only_unverified=True, run_live_checks=False)
    resp = verify_batch_leads(req=req, db=db_session)

    assert resp.total_processed >= 3
    assert resp.average_score > 0.0
    assert len(resp.results) == resp.total_processed

    # Verify that our newly created leads were processed
    processed_ids = {r["lead_id"] for r in resp.results}
    assert lead1.lead_id in processed_ids
    assert lead2.lead_id in processed_ids
    assert lead3.lead_id in processed_ids

    # Refresh and verify buyer scores were updated
    db_session.refresh(lead1)
    db_session.refresh(lead2)
    db_session.refresh(lead3)
    assert lead1.buyer_score > 0.0
    assert lead2.buyer_score > 0.0
    assert lead3.buyer_score > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Human Reviewer Manual Override
# ─────────────────────────────────────────────────────────────────────────────

def test_manual_verification_override_flow(db_session):
    lead = _make_test_lead(
        db_session,
        status="Partially Verified",
        flags=["FLAG_MISSING_WEBSITE", "FLAG_NO_DIRECT_IMPORT_EVIDENCE"],
        buyer_score=65.0,
    )
    initial_score = lead.buyer_score

    # Human reviewer inspects documents and overrides status to Verified
    req = ManualVerificationRequest(
        reviewer_name="Sarah Jenkins (Senior Compliance)",
        status_override="Verified",
        notes="Inspected signed bill of lading and official commercial registry certificate. Buyer is genuine.",
        cleared_flags=["FLAG_NO_DIRECT_IMPORT_EVIDENCE"],
        added_flags=[],
        score_adjustment=20.0,
    )

    updated = manual_lead_verification_override(lead_id=lead.lead_id, req=req, db=db_session)

    assert updated.verification_status == "Verified"
    assert updated.buyer_score == initial_score + 20.0
    assert "FLAG_NO_DIRECT_IMPORT_EVIDENCE" not in updated.risk_flags
    assert "FLAG_MISSING_WEBSITE" in updated.risk_flags
    assert "Sarah Jenkins" in updated.notes
    assert updated.pipeline_stage == "Verified Candidate"


def test_manual_verification_invalid_status_rejected(db_session):
    lead = _make_test_lead(db_session)
    from fastapi import HTTPException

    req = ManualVerificationRequest(
        reviewer_name="Compliance Bot",
        status_override="SuperDuperVerified",  # Invalid
        notes="Trying invalid status",
    )
    with pytest.raises(HTTPException) as exc:
        manual_lead_verification_override(lead_id=lead.lead_id, req=req, db=db_session)
    assert exc.value.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# 4. Audit Trail & Verification Logs
# ─────────────────────────────────────────────────────────────────────────────

def test_lead_audit_trail_history(db_session):
    lead = _make_test_lead(db_session)

    # 1. Trigger automated verification
    trigger_verification(lead_id=lead.lead_id, run_live_checks=False, db=db_session)

    # 2. Trigger human compliance override
    req = ManualVerificationRequest(
        reviewer_name="Compliance Auditor",
        status_override="Verified",
        notes="Second-tier document review completed.",
        score_adjustment=5.0,
    )
    manual_lead_verification_override(lead_id=lead.lead_id, req=req, db=db_session)

    # 3. Retrieve audit trail
    trail = get_lead_audit_trail(lead_id=lead.lead_id, db=db_session)
    assert len(trail) >= 2

    # Most recent should be the human reviewer log
    assert "human_reviewer:Compliance Auditor" in trail[0].verified_by
    # Previous should be the automated engine
    assert "automated_engine" in trail[1].verified_by
