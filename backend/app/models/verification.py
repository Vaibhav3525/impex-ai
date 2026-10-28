from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String(64), ForeignKey("leads.lead_id", ondelete="CASCADE"), index=True, nullable=False)
    
    # 100-Point Score Breakdown
    identity_score = Column(Float, default=0.0)      # Max 20
    relevance_score = Column(Float, default=0.0)     # Max 20
    website_score = Column(Float, default=0.0)       # Max 15
    email_score = Column(Float, default=0.0)         # Max 15
    import_evidence_score = Column(Float, default=0.0) # Max 15
    independent_score = Column(Float, default=0.0)   # Max 15
    total_score = Column(Float, default=0.0)         # Max 100
    
    # Check Details & Evidence Logs
    dns_mx_records = Column(JSON, default=list)
    smtp_check_result = Column(String(50), nullable=True) # Valid, Bounced, Timeout, Untested
    http_status = Column(Integer, nullable=True)
    ssl_valid = Column(String(20), nullable=True)
    domain_age_days = Column(Integer, nullable=True)
    
    # Registry Evidence
    registry_name = Column(String(100), nullable=True)
    registry_company_id = Column(String(100), nullable=True)
    registry_url = Column(Text, nullable=True)
    
    # Risk Assessment
    risk_level = Column(String(20), default="LOW") # LOW, MEDIUM, HIGH, CRITICAL
    detected_flags = Column(JSON, default=list)
    
    # Verification Meta
    verified_by = Column(String(50), default="automated_engine") # automated_engine | human_reviewer
    evidence_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

