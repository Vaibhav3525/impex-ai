import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Boolean
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

def generate_profile_id():
    return f"prod_{uuid.uuid4().hex[:12]}"

class ProductProfile(Base):
    """
    Day 6 — Exporter Product Configuration Model
    PRD §5: Administrators configure product specifications, HS codes,
    target/excluded countries, payment terms, and packaging to match
    against discovered international buyers.
    """
    __tablename__ = "product_profiles"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(String(64), unique=True, index=True, default=generate_profile_id, nullable=False)

    # Product Identification
    product_name = Column(String(255), nullable=False, index=True)
    product_category = Column(String(255), nullable=False, index=True)
    hs_code = Column(String(20), nullable=True, index=True)
    specifications = Column(Text, nullable=True)
    grade = Column(String(100), nullable=True)
    origin_country = Column(String(100), default="India", nullable=False)

    # Supply & Commercial Capabilities
    available_quantity = Column(String(100), nullable=True) # e.g. "500 MT / Month"
    packaging = Column(String(255), nullable=True)          # e.g. "50kg PP Bags, Jute Bags"
    moq = Column(String(100), nullable=True)                # e.g. "1x20ft FCL (20 MT)"
    target_price_min = Column(Float, nullable=True)
    target_price_max = Column(Float, nullable=True)
    currency = Column(String(10), default="USD", nullable=False)
    incoterms = Column(String(50), default="FOB", nullable=False) # FOB, CIF, CFR, EXW

    # Financial & Risk Parameters
    preferred_payment_terms = Column(String(255), default="30% Advance + 70% against BL scan / Irrevocable LC at Sight", nullable=False)

    # Market Geo-Targeting Rules
    target_countries = Column(JSON, default=list)    # e.g. ["Germany", "United Arab Emirates", "Saudi Arabia"]
    excluded_countries = Column(JSON, default=list)  # e.g. ["Sanctioned Nation", "High Risk Country"]

    # Export Readiness & Compliance
    certifications = Column(JSON, default=list)      # e.g. ["APEDA", "FSSAI", "ISO 22000", "HACCP", "HALAL"]
    export_readiness = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, index=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

