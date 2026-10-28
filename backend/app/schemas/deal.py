from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.lead import LeadResponse

PIPELINE_STAGES = [
    "Discovered",
    "Verification Pending",
    "Verified Candidate",
    "Qualified",
    "Outreach Approved",
    "Email Sent",
    "Buyer Replied",
    "Requirements Received",
    "Quotation Prepared",
    "Negotiation",
    "Purchase Order Received",
    "Payment Verification",
    "Order Confirmed",
    "Completed",
    "Lost / Rejected"
]

class DealBase(BaseModel):
    lead_id: str = Field(..., description="Lead ID this deal belongs to")
    product_name: str = Field(..., description="Export commodity or product line")
    hs_code: Optional[str] = None
    required_quantity: Optional[str] = None
    target_price: Optional[float] = None
    currency: str = Field("USD", description="Currency (USD, EUR, etc.)")
    destination_port: Optional[str] = None
    incoterms: Optional[str] = Field("FOB", description="Incoterms (FOB, CIF, CFR, EXW)")
    payment_terms: Optional[str] = Field("30% Advance + 70% against BL", description="Agreed or proposed payment terms")
    stage: str = Field("Discovered", description="Current 15-stage pipeline step")
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

class DealCreate(DealBase):
    pass

class DealUpdate(BaseModel):
    stage: Optional[str] = None
    product_name: Optional[str] = None
    hs_code: Optional[str] = None
    required_quantity: Optional[str] = None
    target_price: Optional[float] = None
    currency: Optional[str] = None
    destination_port: Optional[str] = None
    incoterms: Optional[str] = None
    payment_terms: Optional[str] = None
    payment_risk_status: Optional[str] = None
    payment_risk_notes: Optional[str] = None
    quotation_amount: Optional[float] = None
    confirmed_order_value: Optional[float] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

class DealResponse(DealBase):
    id: int
    deal_id: str
    payment_risk_status: str
    payment_risk_notes: Optional[str] = None
    quotation_amount: Optional[float] = None
    confirmed_order_value: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StageTransitionRequest(BaseModel):
    new_stage: str = Field(..., description="Target pipeline stage from the 15 canonical stages")
    notes: Optional[str] = Field(None, description="Reason or context for moving stage")

class KanbanColumn(BaseModel):
    stage: str
    index: int
    count: int
    leads: List[LeadResponse]
    deals: List[DealResponse]

class KanbanBoardResponse(BaseModel):
    stages: List[KanbanColumn]
    total_leads: int
    total_deals: int

class PipelineFunnelMetric(BaseModel):
    stage: str
    lead_count: int
    deal_count: int
    confirmed_revenue_usd: float

class PipelineSummaryResponse(BaseModel):
    funnel: List[PipelineFunnelMetric]
    total_pipeline_deals_count: int
    total_quotation_value_usd: float
    total_confirmed_revenue_usd: float
