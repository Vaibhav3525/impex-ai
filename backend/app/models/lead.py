from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Index
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String(64), unique=True, index=True, nullable=False)
    
    # Core Company Info
    company_name = Column(String(255), nullable=False, index=True)
    country = Column(String(100), nullable=False, index=True)
    city = Column(String(100), nullable=True)
    website = Column(String(500), nullable=True)
    product_category = Column(String(255), nullable=False, index=True)
    
    # Contact Details
    contact_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    business_email = Column(String(255), nullable=True, index=True)
    phone_number = Column(String(100), nullable=True)
    
    # Provenance & Evidence
    source = Column(String(255), nullable=False)
    source_url = Column(Text, nullable=True)
    import_evidence = Column(Text, nullable=True)
    
    # Verification & Qualification
    verification_status = Column(String(50), default="Unverified", index=True) # Verified, Partially Verified, Unverified, Rejected
    buyer_score = Column(Float, default=0.0, index=True) # 0 to 100
    risk_flags = Column(JSON, default=list) # Array of risk flags
    last_verified = Column(DateTime, nullable=True)
    
    # Day 8: Dedicated Payment Risk Fields (Strict separation: Qualification Score != Payment Risk Score)
    payment_risk_score = Column(Float, default=0.0, index=True) # 0.0 (Clean/Safe) to 100.0 (Critical Risk)
    risk_level = Column(String(20), default="LOW", index=True)   # LOW, MEDIUM, HIGH, CRITICAL

    # Outreach & Pipeline Status
    outreach_status = Column(String(50), default="Not Contacted", index=True) # Not Contacted, Queued, Sent, Replied, Suppressed
    pipeline_stage = Column(String(50), default="Discovered", index=True) # 15 stages
    next_followup = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Deduplication & Hash Fields
    dedup_hash = Column(String(64), unique=True, index=True, nullable=False) # sha256(company_normalized + domain/country)
    
    # Audit Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_lead_country_product", "country", "product_category"),
        Index("idx_lead_score_status", "buyer_score", "verification_status"),
        Index("idx_lead_risk_level", "risk_level", "payment_risk_score"),
    )
