from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

class LeadBase(BaseModel):
    company_name: str = Field(..., description="Legal or trading name of the buyer company")
    country: str = Field(..., description="Country where the buyer is located")
    city: Optional[str] = None
    website: Optional[str] = None
    product_category: str = Field(..., description="Relevant product or commodity category")
    contact_name: Optional[str] = None
    job_title: Optional[str] = None
    business_email: Optional[str] = None
    phone_number: Optional[str] = None
    source: str = Field(..., description="Original data source or directory")
    source_url: Optional[str] = None
    import_evidence: Optional[str] = None
    notes: Optional[str] = None

class LeadCreate(LeadBase):
    pass

class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    website: Optional[str] = None
    product_category: Optional[str] = None
    contact_name: Optional[str] = None
    job_title: Optional[str] = None
    business_email: Optional[str] = None
    phone_number: Optional[str] = None
    verification_status: Optional[str] = None
    buyer_score: Optional[float] = None
    risk_flags: Optional[List[str]] = None
    outreach_status: Optional[str] = None
    pipeline_stage: Optional[str] = None
    notes: Optional[str] = None

class LeadResponse(LeadBase):
    id: int
    lead_id: str
    verification_status: str
    buyer_score: float
    risk_flags: List[str]
    last_verified: Optional[datetime] = None
    outreach_status: str
    pipeline_stage: str
    next_followup: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LeadPagination(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[LeadResponse]

