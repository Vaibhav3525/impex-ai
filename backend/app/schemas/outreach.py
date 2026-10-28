from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class EmailComposeRequest(BaseModel):
    product_profile_id: str = Field(..., description="ID or profile_id of product to offer")
    sequence_step: int = Field(1, ge=1, le=3, description="1 = Introduction, 2 = Day 4 Follow-up, 3 = Day 8 Final Check")
    custom_instructions: Optional[str] = Field(None, description="Optional focus area or specific trade note")

class EmailApprovalRequest(BaseModel):
    reviewer_name: str = Field(..., description="Identity of compliance officer or export manager approving dispatch")
    subject_override: Optional[str] = Field(None, description="Edited email subject line")
    body_override: Optional[str] = Field(None, description="Edited email body text")

class EmailRejectionRequest(BaseModel):
    reviewer_name: str = Field(..., description="Identity of reviewer rejecting the email")
    reason: str = Field(..., description="Required explanation for rejection (e.g. invalid contact, market embargo)")

class OutreachEmailResponse(BaseModel):
    id: int
    email_id: str
    campaign_id: Optional[str] = None
    lead_id: str
    product_id: Optional[str] = None
    to_email: str
    to_name: Optional[str] = None
    company_name: str
    country: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    sequence_step: int
    status: str
    approval_mode: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    confidence_score: float
    grounding_evidence: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SuppressionCreate(BaseModel):
    email: str = Field(..., description="Email address or domain to suppress from all future outreach")
    reason: str = Field("Manual Suppression", description="Hard Bounce | Unsubscribe | Spam Complaint | Manual Suppression")
    notes: Optional[str] = None

class SuppressionResponse(BaseModel):
    id: int
    email: str
    reason: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OutreachQueueSummary(BaseModel):
    total_queued: int
    total_approved: int
    total_rejected: int
    total_sent: int
    pending_emails: List[OutreachEmailResponse]
