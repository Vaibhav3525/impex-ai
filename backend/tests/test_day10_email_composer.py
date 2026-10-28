"""
Day 10 Tests — Mode A Grounded Email Personalization & Outreach Queue API
Tests:
  - Factual grounding & zero-fabrication check (PRD §6 & §10)
  - Localized greetings & salutations (Germany, Middle East, Japan, generic)
  - Sequences 1, 2, and 3 templates
  - Mode A Assisted Queueing (status = Queued by default)
  - Human reviewer approval with optional edits
  - Human reviewer rejection with required justification
  - Suppression list enforcement (blocks draft creation for suppressed recipients)
"""

import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.models.product_profile import ProductProfile
from app.models.outreach import OutreachEmail, SuppressionList
from app.schemas.lead import LeadCreate
from app.schemas.outreach import (
    EmailComposeRequest,
    EmailApprovalRequest,
    EmailRejectionRequest,
    SuppressionCreate,
)
from app.services.lead_service import ingest_lead
from app.services.email_composer import compose_grounded_email, _get_salutation
from app.api.outreach import (
    compose_outreach_email,
    get_outreach_queue,
    approve_outreach_email,
    reject_outreach_email,
    add_to_suppression_list,
)


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _make_outreach_lead(db: Session, country: str = "Germany", contact: str = "Klaus Richter") -> Lead:
    uid = uuid.uuid4().hex[:6]
    lc = LeadCreate(
        company_name=f"Bavaria Gourmet Import {uid}",
        country=country,
        city="Munich",
        website=f"https://bavaria-{uid}.de",
        product_category="Organic Spices & Commodities",
        contact_name=contact,
        job_title="Head of Sourcing",
        business_email=f"sourcing@{uid}-bavaria.de",
        phone_number="+49 89 123456",
        source="Indo-German Chamber",
        source_url="https://indo-german.com",
        import_evidence="Regular commercial importer of organic turmeric and ginger.",
    )
    lead, _ = ingest_lead(db, lc)
    return lead


def _make_outreach_product(db: Session) -> ProductProfile:
    prod = ProductProfile(
        product_name="Organic Alleppey Green Cardamom 8mm",
        product_category="Spices & Seasonings",
        hs_code="09083110",
        specifications="Extra bold 8mm+ pods, deep green color, moisture max 10%, essential oil > 7.5%",
        grade="Grade A Extra Bold",
        origin_country="India",
        available_quantity="25 MT / Month",
        packaging="5kg & 10kg Vacuum Foil Packs in Master Cartons",
        moq="500 kg (Air Freight) / 2 MT (Sea FCL)",
        target_price_min=24.50,
        target_price_max=28.00,
        currency="USD",
        incoterms="FOB Cochin Port",
        preferred_payment_terms="30% Advance + 70% against BL / Irrevocable LC at Sight",
        target_countries=["Germany", "United Arab Emirates", "Saudi Arabia"],
        certifications=["APEDA", "FSSAI", "ISO 22000", "Spice Board India"],
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


# ─────────────────────────────────────────────────────────────────────────────
# 1. Grounded Email Composition & Zero-Fabrication Checks
# ─────────────────────────────────────────────────────────────────────────────

def test_grounded_email_content_verification(db_session):
    lead = _make_outreach_lead(db_session, country="Germany", contact="Hans Schmidt")
    product = _make_outreach_product(db_session)

    composed = compose_grounded_email(lead=lead, product=product, sequence_step=1)

    # 1. Respectful German salutation
    assert "Dear Mr./Ms. Schmidt" in composed["body_text"]

    # 2. Strict grounding — contains exact specs from product profile
    assert product.product_name in composed["body_text"]
    assert "Extra bold 8mm+ pods" in composed["body_text"]
    assert "Vacuum Foil Packs" in composed["body_text"]
    assert "FOB Cochin Port" in composed["body_text"]
    assert "Spice Board India" in composed["body_text"]
    assert "30% Advance + 70% against BL" in composed["body_text"]

    # 3. Confidence score and evidence audit trail
    assert composed["confidence_score"] == 1.0
    assert len(composed["grounding_evidence"]) >= 5
    assert any("Recipient Company" in e for e in composed["grounding_evidence"])
    assert any("Offered Commodity" in e for e in composed["grounding_evidence"])


def test_localized_salutations(db_session):
    # Germany with contact name
    lead_de = _make_outreach_lead(db_session, country="Germany", contact="Peter Becker")
    assert _get_salutation(lead_de) == "Dear Mr./Ms. Becker"

    # Japan with contact name
    lead_jp = _make_outreach_lead(db_session, country="Japan", contact="Kenji Sato")
    assert _get_salutation(lead_jp) == "Dear Sato-san"

    # UAE without contact name
    lead_uae = _make_outreach_lead(db_session, country="United Arab Emirates", contact=None)
    assert "Dear Esteemed Procurement Division" in _get_salutation(lead_uae)


def test_sequence_steps_variation(db_session):
    lead = _make_outreach_lead(db_session)
    product = _make_outreach_product(db_session)

    # Sequence 1: Introduction
    seq1 = compose_grounded_email(lead, product, sequence_step=1)
    assert "Export Inquiry:" in seq1["subject"]
    assert "present our export capabilities" in seq1["body_text"]

    # Sequence 2: Day 4 Follow-up
    seq2 = compose_grounded_email(lead, product, sequence_step=2)
    assert "Follow-up:" in seq2["subject"]
    assert "courier dispatch of physical lab samples" in seq2["body_text"]

    # Sequence 3: Day 8 Closing
    seq3 = compose_grounded_email(lead, product, sequence_step=3)
    assert "Final Inquiry:" in seq3["subject"]
    assert "keep your specifications on file" in seq3["body_text"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. API: Mode A Assisted Queue Workflow
# ─────────────────────────────────────────────────────────────────────────────

def test_compose_outreach_enters_mode_a_queue(db_session):
    lead = _make_outreach_lead(db_session)
    product = _make_outreach_product(db_session)

    req = EmailComposeRequest(
        product_profile_id=product.profile_id,
        sequence_step=1,
    )
    email_obj = compose_outreach_email(lead_id=lead.lead_id, req=req, db=db_session)

    assert email_obj.status == "Queued"
    assert email_obj.approval_mode == "Assisted"
    assert email_obj.to_email == lead.business_email
    assert email_obj.product_id == product.profile_id

    # Lead should move to Outreach Queued
    db_session.refresh(lead)
    assert lead.pipeline_stage == "Outreach Queued"
    assert lead.outreach_status == "Queued"


def test_outreach_queue_summary_api(db_session):
    summary = get_outreach_queue(status_filter="Queued", limit=50, db=db_session)
    assert summary.total_queued >= 1
    assert len(summary.pending_emails) >= 1
    assert all(e.status == "Queued" for e in summary.pending_emails)


def test_human_approval_advances_pipeline(db_session):
    lead = _make_outreach_lead(db_session)
    product = _make_outreach_product(db_session)

    # Compose
    req = EmailComposeRequest(product_profile_id=product.profile_id, sequence_step=1)
    email_obj = compose_outreach_email(lead_id=lead.lead_id, req=req, db=db_session)

    # Human Reviewer Approves with custom subject tweak
    appr_req = EmailApprovalRequest(
        reviewer_name="Michael Scott (Export Manager)",
        subject_override="Premium Organic Cardamom Supply: Offer for Munich Distribution",
    )
    approved = approve_outreach_email(email_id=email_obj.email_id, req=appr_req, db=db_session)

    assert approved.status == "Approved"
    assert approved.approved_by == "Michael Scott (Export Manager)"
    assert approved.approved_at is not None
    assert approved.subject == "Premium Organic Cardamom Supply: Offer for Munich Distribution"

    # Associated lead advances to Outreach Approved
    db_session.refresh(lead)
    assert lead.pipeline_stage == "Outreach Approved"


def test_human_rejection_marks_record(db_session):
    lead = _make_outreach_lead(db_session)
    product = _make_outreach_product(db_session)

    req = EmailComposeRequest(product_profile_id=product.profile_id, sequence_step=1)
    email_obj = compose_outreach_email(lead_id=lead.lead_id, req=req, db=db_session)

    rej_req = EmailRejectionRequest(
        reviewer_name="Compliance Auditor",
        reason="Buyer recently published EU MRL notice requiring different lab certification.",
    )
    rejected = reject_outreach_email(email_id=email_obj.email_id, req=rej_req, db=db_session)

    assert rejected.status == "Rejected"
    assert "Compliance Auditor" in (rejected.rejection_reason or "")
    assert "EU MRL" in (rejected.rejection_reason or "")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Suppression List Guardrails
# ─────────────────────────────────────────────────────────────────────────────

def test_suppression_list_blocks_drafting(db_session):
    lead = _make_outreach_lead(db_session)
    product = _make_outreach_product(db_session)

    # Add lead's email to suppression list
    supp_in = SuppressionCreate(
        email=lead.business_email,
        reason="Unsubscribe",
        notes="Recipient requested removal via phone",
    )
    add_to_suppression_list(supp_in=supp_in, db=db_session)

    # Attempting to compose email for this lead must now be blocked
    req = EmailComposeRequest(product_profile_id=product.profile_id)
    with pytest.raises(HTTPException) as exc:
        compose_outreach_email(lead_id=lead.lead_id, req=req, db=db_session)
    assert exc.value.status_code == 400
    assert "suppressed" in exc.value.detail.lower()

