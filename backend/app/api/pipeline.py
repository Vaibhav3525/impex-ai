"""
Day 9 — 15-Stage CRM Pipeline & Deals Management API Router
PRD §2 & §12: Prospect tracking from initial discovery to quotation, negotiation,
commercial order, and realized export revenue.

Endpoints:
  GET    /api/v1/pipeline/kanban           — Full 15-stage Kanban board data (leads & deals)
  GET    /api/v1/pipeline/summary          — Conversion funnel and realized revenue metrics
  PATCH  /api/v1/pipeline/leads/{id}/stage — Move lead across 15 pipeline stages
  POST   /api/v1/deals                     — Create formal commercial export deal
  GET    /api/v1/deals                     — List deals with multi-criteria filtering
  GET    /api/v1/deals/{deal_id}           — Fetch deal by ID
  PATCH  /api/v1/deals/{deal_id}/stage     — Transition deal stage with audit tracking
  PUT    /api/v1/deals/{deal_id}           — Update deal commercial values
  DELETE /api/v1/deals/{deal_id}           — Remove deal
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.lead import Lead
from app.models.deal import Deal
from app.schemas.lead import LeadResponse
from app.schemas.deal import (
    PIPELINE_STAGES,
    DealCreate,
    DealUpdate,
    DealResponse,
    StageTransitionRequest,
    KanbanColumn,
    KanbanBoardResponse,
    PipelineFunnelMetric,
    PipelineSummaryResponse,
    DealFinancialRiskResponse,
)
from app.services.payment_risk import assess_deal_financial_risk, audit_and_save_deal_risk

router = APIRouter(tags=["CRM Pipeline & Deals"])

def _generate_deal_id():
    return f"DEAL-{uuid.uuid4().hex[:8].upper()}"

def _validate_stage(stage: str):
    if stage not in PIPELINE_STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pipeline stage '{stage}'. Must be one of: {', '.join(PIPELINE_STAGES)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Kanban Board & Pipeline Funnel Analytics
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/pipeline/kanban", response_model=KanbanBoardResponse)
def get_kanban_board(db: Session = Depends(get_db)):
    """
    Returns all 15 stages populated with leads and deals for the CRM Kanban dashboard.
    """
    all_leads = db.query(Lead).all()
    all_deals = db.query(Deal).all()

    # Group leads and deals by stage
    leads_by_stage = {s: [] for s in PIPELINE_STAGES}
    deals_by_stage = {s: [] for s in PIPELINE_STAGES}

    for l in all_leads:
        stage = l.pipeline_stage if l.pipeline_stage in leads_by_stage else "Discovered"
        leads_by_stage[stage].append(LeadResponse.model_validate(l))

    for d in all_deals:
        stage = d.stage if d.stage in deals_by_stage else "Discovered"
        deals_by_stage[stage].append(DealResponse.model_validate(d))

    columns = []
    for idx, s in enumerate(PIPELINE_STAGES):
        s_leads = leads_by_stage[s]
        s_deals = deals_by_stage[s]
        columns.append(KanbanColumn(
            stage=s,
            index=idx + 1,
            count=len(s_leads) + len(s_deals),
            leads=s_leads,
            deals=s_deals,
        ))

    return KanbanBoardResponse(
        stages=columns,
        total_leads=len(all_leads),
        total_deals=len(all_deals),
    )


@router.get("/pipeline/summary", response_model=PipelineSummaryResponse)
def get_pipeline_summary(db: Session = Depends(get_db)):
    """
    Computes conversion funnel metrics and confirmed commercial export revenue.
    PRD Invariant: Revenue tracks actual confirmed orders only — no fabricated estimates.
    """
    funnel_metrics: List[PipelineFunnelMetric] = []
    total_quote_val = 0.0
    total_confirmed_rev = 0.0

    all_deals = db.query(Deal).all()
    total_deal_count = len(all_deals)

    for s in PIPELINE_STAGES:
        s_leads_count = db.query(Lead).filter(Lead.pipeline_stage == s).count()
        s_deals = [d for d in all_deals if d.stage == s]
        s_deals_count = len(s_deals)

        confirmed_val = sum(d.confirmed_order_value or 0.0 for d in s_deals)
        funnel_metrics.append(PipelineFunnelMetric(
            stage=s,
            lead_count=s_leads_count,
            deal_count=s_deals_count,
            confirmed_revenue_usd=round(confirmed_val, 2),
        ))

    for d in all_deals:
        if d.quotation_amount:
            total_quote_val += d.quotation_amount
        if d.confirmed_order_value and d.stage in {"Order Confirmed", "Completed"}:
            total_confirmed_rev += d.confirmed_order_value

    return PipelineSummaryResponse(
        funnel=funnel_metrics,
        total_pipeline_deals_count=total_deal_count,
        total_quotation_value_usd=round(total_quote_val, 2),
        total_confirmed_revenue_usd=round(total_confirmed_rev, 2),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Lead Stage Transitions
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/pipeline/leads/{lead_id}/stage", response_model=LeadResponse)
def update_lead_pipeline_stage(
    lead_id: str,
    req: StageTransitionRequest,
    db: Session = Depends(get_db),
):
    """
    Transitions a buyer lead to a new step in the 15-stage CRM pipeline.
    Validates stage legitimacy and logs the transition into lead notes.
    """
    _validate_stage(req.new_stage)

    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found.")

    old_stage = lead.pipeline_stage
    lead.pipeline_stage = req.new_stage
    lead.updated_at = datetime.now(timezone.utc)

    # Append audit trail
    ts_str = lead.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    note_msg = f"[Stage Change at {ts_str}]: '{old_stage}' -> '{req.new_stage}'"
    if req.notes:
        note_msg += f" (Context: {req.notes})"

    if lead.notes:
        lead.notes = f"{lead.notes}\n{note_msg}"
    else:
        lead.notes = note_msg

    db.commit()
    db.refresh(lead)
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# 3. Deal CRUD & Stage Management
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/deals", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    deal_in: DealCreate,
    db: Session = Depends(get_db),
):
    """
    Creates a commercial export transaction deal associated with a verified lead.
    """
    _validate_stage(deal_in.stage)

    lead = db.query(Lead).filter(Lead.lead_id == deal_in.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Associated lead '{deal_in.lead_id}' not found.")

    deal_dict = deal_in.model_dump()
    deal_dict["deal_id"] = _generate_deal_id()
    
    new_deal = Deal(**deal_dict)
    db.add(new_deal)
    db.commit()
    db.refresh(new_deal)
    return new_deal


@router.get("/deals", response_model=List[DealResponse])
def list_deals(
    stage: Optional[str] = None,
    lead_id: Optional[str] = None,
    currency: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Lists active commercial export deals with optional filtering.
    """
    query = db.query(Deal)
    if stage:
        query = query.filter(Deal.stage == stage)
    if lead_id:
        query = query.filter(Deal.lead_id == lead_id)
    if currency:
        query = query.filter(Deal.currency == currency)

    return query.order_by(desc(Deal.created_at)).limit(limit).all()


@router.get("/deals/{deal_id}", response_model=DealResponse)
def get_deal(deal_id: str, db: Session = Depends(get_db)):
    """
    Fetches complete commercial terms and state for a specific deal.
    """
    deal = db.query(Deal).filter(Deal.deal_id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal '{deal_id}' not found.")
    return deal


@router.patch("/deals/{deal_id}/stage", response_model=DealResponse)
def update_deal_stage(
    deal_id: str,
    req: StageTransitionRequest,
    db: Session = Depends(get_db),
):
    """
    Advances a deal through the 15 sales stages.
    """
    _validate_stage(req.new_stage)

    deal = db.query(Deal).filter(Deal.deal_id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal '{deal_id}' not found.")

    old_stage = deal.stage
    deal.stage = req.new_stage
    deal.updated_at = datetime.now(timezone.utc)

    # Note update
    ts_str = deal.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    note_msg = f"[Deal Stage Update at {ts_str}]: '{old_stage}' -> '{req.new_stage}'"
    if req.notes:
        note_msg += f" ({req.notes})"

    if deal.notes:
        deal.notes = f"{deal.notes}\n{note_msg}"
    else:
        deal.notes = note_msg

    db.commit()
    db.refresh(deal)
    return deal


@router.put("/deals/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: str,
    updates: DealUpdate,
    db: Session = Depends(get_db),
):
    """
    Updates quotation amount, confirmed order value, or incoterms for a deal.
    """
    deal = db.query(Deal).filter(Deal.deal_id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal '{deal_id}' not found.")

    update_data = updates.model_dump(exclude_unset=True)
    if "stage" in update_data and update_data["stage"]:
        _validate_stage(update_data["stage"])

    for k, v in update_data.items():
        setattr(deal, k, v)

    deal.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(deal)
    return deal


@router.delete("/deals/{deal_id}", status_code=status.HTTP_200_OK)
def delete_deal(deal_id: str, db: Session = Depends(get_db)):
    """
    Deletes a deal record.
    """
    deal = db.query(Deal).filter(Deal.deal_id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal '{deal_id}' not found.")

    db.delete(deal)
    db.commit()
    return {"message": f"Deal '{deal_id}' successfully removed.", "status": "deleted"}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Transaction Financial Safety & Commercial Risk
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/deals/{deal_id}/financial-risk", response_model=DealFinancialRiskResponse)
def evaluate_and_audit_deal_financial_risk(deal_id: str, db: Session = Depends(get_db)):
    """
    Evaluates commercial deal payment terms against buyer risk status and order exposure.
    Persists payment risk rating to deal records.
    PRD Rule: High-risk payment terms (OA/DA) require human approval and are flagged/blocked.
    """
    deal = db.query(Deal).filter(Deal.deal_id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal '{deal_id}' not found.")

    lead = db.query(Lead).filter(Lead.lead_id == deal.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Associated lead '{deal.lead_id}' not found.")

    assessment = audit_and_save_deal_risk(db, deal, lead)
    return DealFinancialRiskResponse(**assessment)


@router.get("/deals/{deal_id}/financial-risk", response_model=DealFinancialRiskResponse)
def get_deal_financial_risk(deal_id: str, db: Session = Depends(get_db)):
    """
    Retrieves dynamic commercial financial risk assessment for an export deal without modifying state.
    """
    deal = db.query(Deal).filter(Deal.deal_id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail=f"Deal '{deal_id}' not found.")

    lead = db.query(Lead).filter(Lead.lead_id == deal.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Associated lead '{deal.lead_id}' not found.")

    assessment = assess_deal_financial_risk(deal, lead)
    return DealFinancialRiskResponse(**assessment)

