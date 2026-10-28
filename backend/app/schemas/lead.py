from datetime import datetime
from typing import Optional, List, Dict, Any
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
    payment_risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    risk_flags: Optional[List[str]] = None
    outreach_status: Optional[str] = None
    pipeline_stage: Optional[str] = None
    notes: Optional[str] = None

class LeadResponse(LeadBase):
    id: int
    lead_id: str
    verification_status: str
    buyer_score: float
    payment_risk_score: float = 0.0
    risk_level: str = "LOW"
    risk_flags: List[str] = Field(default_factory=list)
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

class ManualVerificationRequest(BaseModel):
    reviewer_name: str = Field(..., description="Name or identifier of the compliance officer / human reviewer")
    status_override: Optional[str] = Field(None, description="Override status: 'Verified', 'Partially Verified', 'Rejected', or 'Unverified'")
    notes: str = Field(..., description="Factual audit justification for the manual verification change")
    cleared_flags: Optional[List[str]] = Field(default_factory=list, description="Risk flags cleared after human investigation")
    added_flags: Optional[List[str]] = Field(default_factory=list, description="New risk flags identified during manual review")
    score_adjustment: Optional[float] = Field(None, description="Direct adjustment to buyer_score (-50.0 to +50.0)")

class BatchVerifyRequest(BaseModel):
    limit: int = Field(50, ge=1, le=500, description="Maximum number of leads to verify in this batch")
    only_unverified: bool = Field(True, description="Only process leads with status 'Unverified'")
    run_live_checks: bool = Field(False, description="Perform live DNS/TLS socket probes (slower)")

class BatchVerifyResponse(BaseModel):
    total_processed: int
    verified_count: int
    partially_verified_count: int
    unverified_count: int
    average_score: float
    results: List[Dict[str, Any]]

class VerificationLogResponse(BaseModel):
    id: int
    lead_id: str
    identity_score: float
    relevance_score: float
    website_score: float
    email_score: float
    import_evidence_score: float
    independent_score: float
    total_score: float
    dns_mx_records: Optional[List[str]] = None
    smtp_check_result: Optional[str] = None
    http_status: Optional[int] = None
    ssl_valid: Optional[str] = None
    domain_age_days: Optional[int] = None
    risk_level: str
    detected_flags: List[str]
    verified_by: str
    evidence_summary: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RiskSignal(BaseModel):
    flag: str
    severity: str # CRITICAL | HIGH | MEDIUM | LOW
    points: float
    description: str
    evidence: str

class RiskAssessmentResponse(BaseModel):
    lead_id: str
    company_name: str
    country: str
    buyer_score: float # Commercial qualification score
    payment_risk_score: float # Distinct payment risk score (0-100)
    risk_level: str # LOW | MEDIUM | HIGH | CRITICAL
    detected_signals: List[RiskSignal]
    requires_human_approval: bool
    is_safe_for_automated_outreach: bool
    summary: str
    recommended_mitigation: str
    assessed_at: datetime
