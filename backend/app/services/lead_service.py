import re
import hashlib
import uuid
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.schemas.lead import LeadCreate

def normalize_company_name(name: str) -> str:
    """Normalize legal suffixes, punctuation, and casing to prevent duplicates."""
    cleaned = name.lower().strip()
    # Strip common legal suffixes
    suffixes = [
        r"\bltd\b", r"\blimited\b", r"\binc\b", r"\bcorp\b", r"\bcorporation\b",
        r"\bllc\b", r"\bgmbh\b", r"\bsa\b", r"\bsrl\b", r"\bpvt\b", r"\bco\b"
    ]
    for s in suffixes:
        cleaned = re.sub(s, "", cleaned)
    # Remove special chars and excessive whitespace
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return " ".join(cleaned.split())

def extract_domain(url_or_email: Optional[str]) -> str:
    """Extract clean base domain from URL or email address."""
    if not url_or_email:
        return ""
    text = url_or_email.lower().strip()
    if "@" in text:
        text = text.split("@")[-1]
    # Remove protocol and path
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"^www\.", "", text)
    return text.split("/")[0].split(":")[0].strip()

def generate_dedup_hash(company_name: str, country: str, website: Optional[str] = None, email: Optional[str] = None) -> str:
    """Generate deterministic SHA-256 hash for duplicate detection."""
    norm_name = normalize_company_name(company_name)
    domain = extract_domain(website) or extract_domain(email)
    norm_country = country.lower().strip()
    
    key = f"{norm_name}|{domain}|{norm_country}" if domain else f"{norm_name}|{norm_country}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

def ingest_lead(db: Session, lead_in: LeadCreate) -> Tuple[Lead, bool]:
    """
    Ingests a lead record with duplicate detection.
    Returns (lead, is_created).
    """
    dedup_hash = generate_dedup_hash(
        lead_in.company_name,
        lead_in.country,
        lead_in.website,
        lead_in.business_email
    )
    
    existing = db.query(Lead).filter(Lead.dedup_hash == dedup_hash).first()
    if existing:
        # Update missing fields if new information was provided
        updated = False
        if not existing.business_email and lead_in.business_email:
            existing.business_email = lead_in.business_email
            updated = True
        if not existing.website and lead_in.website:
            existing.website = lead_in.website
            updated = True
        if not existing.contact_name and lead_in.contact_name:
            existing.contact_name = lead_in.contact_name
            updated = True
        if updated:
            db.commit()
            db.refresh(existing)
        return existing, False

    # Create new lead
    lead_id = f"LID-{uuid.uuid4().hex[:8].upper()}"
    new_lead = Lead(
        lead_id=lead_id,
        company_name=lead_in.company_name.strip(),
        country=lead_in.country.strip(),
        city=lead_in.city.strip() if lead_in.city else None,
        website=lead_in.website.strip() if lead_in.website else None,
        product_category=lead_in.product_category.strip(),
        contact_name=lead_in.contact_name.strip() if lead_in.contact_name else None,
        job_title=lead_in.job_title.strip() if lead_in.job_title else None,
        business_email=lead_in.business_email.strip() if lead_in.business_email else None,
        phone_number=lead_in.phone_number.strip() if lead_in.phone_number else None,
        source=lead_in.source.strip(),
        source_url=lead_in.source_url.strip() if lead_in.source_url else None,
        import_evidence=lead_in.import_evidence.strip() if lead_in.import_evidence else None,
        notes=lead_in.notes.strip() if lead_in.notes else None,
        dedup_hash=dedup_hash,
        verification_status="Unverified",
        buyer_score=0.0,
        risk_flags=[],
        outreach_status="Not Contacted",
        pipeline_stage="Discovered"
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    return new_lead, True

