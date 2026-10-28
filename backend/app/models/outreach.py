import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey, Boolean
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

def generate_email_id():
    return f"EML-{uuid.uuid4().hex[:10].upper()}"

def generate_campaign_id():
    return f"CMP-{uuid.uuid4().hex[:8].upper()}"

class OutreachCampaign(Base):
    __tablename__ = "outreach_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(String(64), unique=True, index=True, default=generate_campaign_id, nullable=False)
    name = Column(String(255), nullable=False)
    product_profile_id = Column(String(64), nullable=True) # Linked product profile
    
    status = Column(String(50), default="Draft", index=True) # Draft, Active, Paused, Completed
    daily_limit = Column(Integer, default=50)
    total_sent = Column(Integer, default=0)
    total_opened = Column(Integer, default=0)
    total_replied = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class OutreachEmail(Base):
    """
    Day 10 — Mode A Assisted Outreach Queue Model
    PRD §6 & §10: Grounded email personalization. All outbound emails remain in
    'Queued' status awaiting human inspection before dispatch.
    """
    __tablename__ = "outreach_emails"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(String(64), unique=True, index=True, default=generate_email_id, nullable=False)
    campaign_id = Column(String(64), ForeignKey("outreach_campaigns.campaign_id", ondelete="SET NULL"), nullable=True)
    lead_id = Column(String(64), ForeignKey("leads.lead_id", ondelete="CASCADE"), index=True, nullable=False)
    product_id = Column(String(64), nullable=True)

    # Recipient
    to_email = Column(String(255), nullable=False, index=True)
    to_name = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)

    # Email Content (Strictly Grounded)
    subject = Column(String(500), nullable=False)
    body_text = Column(Text, nullable=False)
    body_html = Column(Text, nullable=True)
    sequence_step = Column(Integer, default=1) # 1 = Initial Outreach, 2 = Day 4 Follow-up, 3 = Day 8 Closing

    # Status & Approval Tracking
    # Queued, Approved, Rejected, Sent, Failed, Replied, Suppressed
    status = Column(String(50), default="Queued", index=True, nullable=False)
    approval_mode = Column(String(20), default="Assisted", nullable=False) # Assisted (Mode A) | Automated (Mode B)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Dispatch & Delivery Info
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Verification & Grounding Evidence Audit
    confidence_score = Column(Float, default=1.0)
    grounding_evidence = Column(JSON, default=list) # Audit of exact real data fields referenced

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class SuppressionList(Base):
    """
    Suppression registry for unsubscribes, hard bounces, and blacklisted domains.
    """
    __tablename__ = "suppression_list"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    reason = Column(String(100), default="Manual Suppression", nullable=False) # Hard Bounce, Unsubscribe, Spam Complaint, Manual
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
