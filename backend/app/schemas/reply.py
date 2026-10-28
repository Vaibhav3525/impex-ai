from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

REPLY_CLASSES = [
    "Interested Buyer",
    "Request for Quotation",
    "Request for Specs",
    "Samples",
    "Price Negotiation",
    "Payment Terms",
    "Future Requirement",
    "Not Interested",
    "Wrong Contact",
    "Potential Scam",
    "Requires Human Review",
]

class IncomingReplyRequest(BaseModel):
    lead_id: str = Field(..., description="Lead ID of the responding buyer")
    from_email: str = Field(..., description="Sender email address")
    subject: str = Field(..., description="Subject line of incoming response")
    raw_body: str = Field(..., description="Raw email text body received from buyer")
    deal_id: Optional[str] = Field(None, description="Optional linked deal ID")

class ReplyReviewRequest(BaseModel):
    reviewer_name: str = Field(..., description="Compliance officer or export manager reviewing classification")
    classification_override: Optional[str] = Field(None, description="Corrected class if model misclassified")
    human_notes: str = Field(..., description="Audit notes or instructions for sales desk")

class BuyerReplyResponse(BaseModel):
    id: int
    lead_id: str
    deal_id: Optional[str] = None
    from_email: str
    subject: str
    raw_body: str
    received_at: datetime
    classification: str
    confidence_score: float
    extracted_product: Optional[str] = None
    extracted_quantity: Optional[str] = None
    extracted_target_price: Optional[float] = None
    extracted_delivery_port: Optional[str] = None
    extracted_payment_method: Optional[str] = None
    extracted_next_action: Optional[str] = None
    reviewed_by_human: str
    human_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ClassificationResult(BaseModel):
    classification: str
    confidence_score: float
    extracted_product: Optional[str] = None
    extracted_quantity: Optional[str] = None
    extracted_target_price: Optional[float] = None
    extracted_delivery_port: Optional[str] = None
    extracted_payment_method: Optional[str] = None
    extracted_next_action: Optional[str] = None
    suggested_pipeline_stage: str

