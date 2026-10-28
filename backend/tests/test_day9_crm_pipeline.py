"""
Day 9 Tests — 15-Stage CRM Deal Pipeline & Kanban API
Tests:
  - Full 15-stage Kanban board generation (all stages populated)
  - Lead stage transition with audit logging
  - Invalid stage rejection (400 validation)
  - Deal CRUD lifecycle & stage advancement
  - Revenue tracking (actual confirmed order values only)
  - Pipeline summary funnel metrics
"""

import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.models.deal import Deal
from app.schemas.lead import LeadCreate
from app.schemas.deal import (
    PIPELINE_STAGES,
    DealCreate,
    DealUpdate,
    StageTransitionRequest,
)
from app.services.lead_service import ingest_lead
from app.api.pipeline import (
    get_kanban_board,
    get_pipeline_summary,
    update_lead_pipeline_stage,
    create_deal,
    list_deals,
    get_deal,
    update_deal_stage,
    update_deal,
    delete_deal,
)


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _make_pipeline_lead(db: Session, stage: str = "Discovered") -> Lead:
    uid = uuid.uuid4().hex[:6]
    lc = LeadCreate(
        company_name=f"Global Trade House {uid}",
        country="United Arab Emirates",
        city="Dubai",
        website=f"https://gth-{uid}.ae",
        product_category="Basmati Rice & Spices",
        contact_name="Rashid Al-Falasi",
        job_title="Procurement Director",
        business_email=f"rashid@{uid}-gth.ae",
        phone_number="+971 4 222 3333",
        source="Dubai Chamber Directory",
        source_url="https://dubaichamber.com",
        import_evidence="Major distributor of grains and commodities in GCC.",
    )
    lead, _ = ingest_lead(db, lc)
    lead.pipeline_stage = stage
    db.commit()
    db.refresh(lead)
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# 1. Kanban Board & Canonical Stages
# ─────────────────────────────────────────────────────────────────────────────

def test_kanban_board_contains_all_15_stages(db_session):
    # Ensure at least one lead exists in some stage
    _make_pipeline_lead(db_session, stage="Discovered")
    _make_pipeline_lead(db_session, stage="Verified Candidate")

    board = get_kanban_board(db=db_session)
    assert len(board.stages) == 15

    stage_names = [col.stage for col in board.stages]
    assert stage_names == PIPELINE_STAGES
    assert board.total_leads >= 2


# ─────────────────────────────────────────────────────────────────────────────
# 2. Lead Stage Transitions
# ─────────────────────────────────────────────────────────────────────────────

def test_lead_stage_transition_success(db_session):
    lead = _make_pipeline_lead(db_session, stage="Discovered")

    req = StageTransitionRequest(
        new_stage="Verified Candidate",
        notes="Automated technical verification and domain enrichment completed with score 88/100.",
    )
    updated = update_lead_pipeline_stage(lead_id=lead.lead_id, req=req, db=db_session)

    assert updated.pipeline_stage == "Verified Candidate"
    assert "Discovered" in updated.notes
    assert "Verified Candidate" in updated.notes
    assert "score 88/100" in updated.notes


def test_lead_stage_transition_invalid_stage_rejected(db_session):
    lead = _make_pipeline_lead(db_session)
    req = StageTransitionRequest(new_stage="NonExistentFantasyStage")

    with pytest.raises(HTTPException) as exc:
        update_lead_pipeline_stage(lead_id=lead.lead_id, req=req, db=db_session)
    assert exc.value.status_code == 400
    assert "Invalid pipeline stage" in exc.value.detail


# ─────────────────────────────────────────────────────────────────────────────
# 3. Deal Creation & Lifecycle Management
# ─────────────────────────────────────────────────────────────────────────────

def test_deal_crud_lifecycle(db_session):
    lead = _make_pipeline_lead(db_session, stage="Qualified")

    # 1. Create Deal
    deal_in = DealCreate(
        lead_id=lead.lead_id,
        product_name="1121 Steam Basmati Rice",
        hs_code="10063020",
        required_quantity="5x20ft Containers (100 MT)",
        target_price=1180.0,
        currency="USD",
        destination_port="Jebel Ali, Dubai",
        incoterms="CIF Jebel Ali",
        payment_terms="30% Advance + 70% against BL",
        stage="Requirements Received",
        assigned_to="Export Director (Sales Desk)",
        notes="Buyer requested 25kg non-woven packaging.",
    )
    created_deal = create_deal(deal_in=deal_in, db=db_session)

    assert created_deal.id is not None
    assert created_deal.deal_id.startswith("DEAL-")
    assert created_deal.stage == "Requirements Received"
    assert created_deal.lead_id == lead.lead_id

    # 2. Retrieve Deal
    fetched = get_deal(deal_id=created_deal.deal_id, db=db_session)
    assert fetched.deal_id == created_deal.deal_id

    # 3. Update Deal Commercial Quotation
    updates = DealUpdate(
        quotation_amount=118000.0,
        confirmed_order_value=115000.0,
        stage="Quotation Prepared",
    )
    updated_deal = update_deal(deal_id=created_deal.deal_id, updates=updates, db=db_session)
    assert updated_deal.quotation_amount == 118000.0
    assert updated_deal.confirmed_order_value == 115000.0
    assert updated_deal.stage == "Quotation Prepared"

    # 4. Advance Stage to Order Confirmed
    stage_req = StageTransitionRequest(new_stage="Order Confirmed", notes="Contract signed and 30% advance received.")
    staged_deal = update_deal_stage(deal_id=created_deal.deal_id, req=stage_req, db=db_session)
    assert staged_deal.stage == "Order Confirmed"
    assert "Contract signed" in staged_deal.notes

    # 5. List Deals with Filter
    deal_list = list_deals(stage="Order Confirmed", db=db_session)
    assert len(deal_list) >= 1
    assert any(d.deal_id == created_deal.deal_id for d in deal_list)

    # 6. Delete Deal
    del_res = delete_deal(deal_id=created_deal.deal_id, db=db_session)
    assert del_res["status"] == "deleted"

    with pytest.raises(HTTPException) as exc:
        get_deal(deal_id=created_deal.deal_id, db=db_session)
    assert exc.value.status_code == 404


def test_create_deal_with_invalid_lead_rejected(db_session):
    deal_in = DealCreate(
        lead_id="LID-NONEXISTENT",
        product_name="Organic Spices",
    )
    with pytest.raises(HTTPException) as exc:
        create_deal(deal_in=deal_in, db=db_session)
    assert exc.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 4. Pipeline Summary & Actual Revenue Tracking
# ─────────────────────────────────────────────────────────────────────────────

def test_pipeline_summary_tracks_actual_revenue(db_session):
    lead = _make_pipeline_lead(db_session)

    # Create confirmed deal
    deal_in = DealCreate(
        lead_id=lead.lead_id,
        product_name="Malabar Black Pepper 550GL",
        stage="Order Confirmed",
        notes="Test confirmed deal for revenue calculation",
    )
    confirmed_deal = create_deal(deal_in=deal_in, db=db_session)
    update_deal(
        deal_id=confirmed_deal.deal_id,
        updates=DealUpdate(
            quotation_amount=45000.0,
            confirmed_order_value=42000.0,
        ),
        db=db_session,
    )

    summary = get_pipeline_summary(db=db_session)

    assert len(summary.funnel) == 15
    assert summary.total_pipeline_deals_count >= 1
    assert summary.total_confirmed_revenue_usd >= 42000.0
    assert summary.total_quotation_value_usd >= 45000.0

