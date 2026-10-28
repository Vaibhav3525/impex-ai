from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey, Numeric
from app.core.database import Base

class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(String(64), unique=True, index=True, nullable=False)
    lead_id = Column(String(64), ForeignKey("leads.lead_id", ondelete="CASCADE"), index=True, nullable=False)
    
    # 15 Pipeline Stages:
    # 1. Discovered, 2. Verification Pending, 3. Verified Candidate, 4. Qualified,
    # 5. Outreach Approved, 6. Email Sent, 7. Buyer Replied, 8. Requirements Received,
    # 9. Quotation Prepared, 10. Negotiation, 11. Purchase Order Received,
    # 12. Payment Verification, 13. Order Confirmed, 14. Completed, 15. Lost / Rejected
    stage = Column(String(50), default="Discovered", index=True, nullable=False)
    
    # Product & Transaction Specifics
    product_name = Column(String(255), nullable=False)
    hs_code = Column(String(20), nullable=True)
    required_quantity = Column(String(100), nullable=True)
    target_price = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    destination_port = Column(String(100), nullable=True)
    incoterms = Column(String(20), nullable=True) # FOB, CIF, CFR, EXW
    
    # Payment Terms & Risk Controls
    # Advance, Irrevocable LC, D/P, D/A, Open Account, Escrow, Unclear
    payment_terms = Column(String(50), nullable=True)
    payment_risk_status = Column(String(50), default="Pending Review") # Approved, Flagged, Under Review, Blocked
    payment_risk_notes = Column(Text, nullable=True)
    
    # Commercial Values (Actual Recorded Values only)
    quotation_amount = Column(Float, nullable=True)
    confirmed_order_value = Column(Float, nullable=True)
    
    # Status & Audit
    assigned_to = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class BuyerReply(Base):
    __tablename__ = "buyer_replies"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String(64), ForeignKey("leads.lead_id", ondelete="CASCADE"), index=True, nullable=False)
    deal_id = Column(String(64), ForeignKey("deals.deal_id", ondelete="SET NULL"), nullable=True)
    
    # Email Metadata
    from_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    raw_body = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 11-Class Response Category
    # 1. Interested Buyer, 2. Request for Quotation, 3. Request for Specs, 4. Samples,
    # 5. Price Negotiation, 6. Payment Terms, 7. Future Requirement, 8. Not Interested,
    # 9. Wrong Contact, 10. Potential Scam, 11. Requires Human Review
    classification = Column(String(50), nullable=False, index=True)
    confidence_score = Column(Float, default=0.0)
    
    # Structured Extracted Entities
    extracted_product = Column(String(255), nullable=True)
    extracted_quantity = Column(String(100), nullable=True)
    extracted_target_price = Column(Float, nullable=True)
    extracted_delivery_port = Column(String(100), nullable=True)
    extracted_payment_method = Column(String(100), nullable=True)
    extracted_next_action = Column(String(255), nullable=True)
    
    # Human Review Status
    reviewed_by_human = Column(String(50), default="PENDING") # PENDING, APPROVED, OVERRIDDEN
    human_notes = Column(Text, nullable=True)
