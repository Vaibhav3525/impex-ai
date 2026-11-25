from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.core.database import Base

class ReviewedEvidence(Base):
    __tablename__ = "reviewed_evidence"
    id = Column(Integer, primary_key=True)
    lead_id = Column(String(64), ForeignKey("leads.lead_id"), nullable=False, index=True)
    category = Column(String(30), nullable=False)
    source_url = Column(Text, nullable=False)
    document_reference = Column(Text, nullable=False)
    finding = Column(Text, nullable=False)
    reviewed_by = Column(String(100), nullable=False)
    reviewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
