import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.models.verification import VerificationLog

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "protonmail.com", "icloud.com", "mail.com", "zoho.com", "yandex.com",
    "tempmail.com", "mailinator.com", "guerrillamail.com", "10minutemail.com"
}

def evaluate_email_quality(email: str | None) -> Tuple[float, List[str]]:
    """Checks email domain credibility and flags free or disposable domains."""
    if not email or "@" not in email:
        return 0.0, ["FLAG_MISSING_EMAIL"]
    
    domain = email.split("@")[-1].lower().strip()
    flags = []
    
    if domain in FREE_EMAIL_DOMAINS:
        flags.append("FLAG_FREE_EMAIL_DOMAIN")
        return 2.0, flags  # Minimal points for personal/disposable email
    
    # Valid corporate domain format
    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", domain):
        return 15.0, []  # Full 15 points
    
    return 5.0, ["FLAG_SUSPICIOUS_EMAIL_SYNTAX"]

def run_lead_verification(db: Session, lead: Lead) -> VerificationLog:
    """
    Executes the 100-point verification model against the lead.
    Enforces evidence-based scoring and autonomous risk flag detection.
    """
    identity_score = 0.0
    relevance_score = 0.0
    website_score = 0.0
    email_score = 0.0
    import_evidence_score = 0.0
    independent_score = 0.0
    detected_flags = []

    # 1. Company Identity & Registration Check (Max 20)
    if lead.company_name and len(lead.company_name.strip()) > 2:
        identity_score += 10.0
    if lead.country and lead.city:
        identity_score += 5.0
    if lead.source and "registry" in lead.source.lower():
        identity_score += 5.0

    # 2. Product & Industry Relevance (Max 20)
    if lead.product_category and len(lead.product_category.strip()) > 0:
        relevance_score += 12.0
    if lead.job_title and any(k in lead.job_title.lower() for k in ["procurement", "purchase", "buyer", "import", "sourcing", "director", "owner"]):
        relevance_score += 8.0

    # 3. Website & Business Identity Consistency (Max 15)
    if lead.website:
        if lead.website.startswith("http://") or lead.website.startswith("https://"):
            website_score += 8.0
        if "https://" in lead.website:
            website_score += 4.0
        if lead.contact_name:
            website_score += 3.0
    else:
        detected_flags.append("FLAG_MISSING_WEBSITE")

    # 4. Business Email Verification (Max 15)
    e_score, e_flags = evaluate_email_quality(lead.business_email)
    email_score = e_score
    detected_flags.extend(e_flags)

    # 5. Evidence of Import Activity (Max 15)
    if lead.import_evidence and len(lead.import_evidence.strip()) > 10:
        import_evidence_score += 15.0
    elif lead.source and any(s in lead.source.lower() for s in ["apeda", "dgft", "customs", "comtrade", "embassy"]):
        import_evidence_score += 10.0
    else:
        detected_flags.append("FLAG_NO_DIRECT_IMPORT_EVIDENCE")

    # 6. Independent Supporting Evidence (Max 15)
    if lead.phone_number:
        independent_score += 5.0
    if lead.source_url:
        independent_score += 5.0
    if lead.contact_name and lead.job_title:
        independent_score += 5.0

    total_score = round(
        identity_score + relevance_score + website_score + email_score + import_evidence_score + independent_score,
        1
    )

    # Determine Verification Status based on PRD Thresholds
    # 80-100: High Priority Candidate
    # 60-79: Potential Candidate requiring additional verification
    # Below 60: Low Priority / Unverified
    if total_score >= 80.0 and "FLAG_FREE_EMAIL_DOMAIN" not in detected_flags:
        status = "Verified"
    elif total_score >= 60.0:
        status = "Partially Verified"
    else:
        status = "Unverified"

    # Assess overall Risk Level
    if "FLAG_FREE_EMAIL_DOMAIN" in detected_flags or "FLAG_ADVANCE_FEE_SCAM" in detected_flags:
        risk_level = "HIGH"
    elif len(detected_flags) >= 2:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Save Verification Log
    log = VerificationLog(
        lead_id=lead.lead_id,
        identity_score=identity_score,
        relevance_score=relevance_score,
        website_score=website_score,
        email_score=email_score,
        import_evidence_score=import_evidence_score,
        independent_score=independent_score,
        total_score=total_score,
        risk_level=risk_level,
        detected_flags=detected_flags,
        evidence_summary=f"Automated evaluation scored {total_score}/100. Verification Status: {status}. Risk Level: {risk_level}."
    )
    db.add(log)

    # Update Lead record
    lead.buyer_score = total_score
    lead.verification_status = status
    lead.risk_flags = detected_flags
    lead.last_verified = datetime.now(timezone.utc)
    if status == "Verified" and lead.pipeline_stage == "Discovered":
        lead.pipeline_stage = "Verified Candidate"

    db.commit()
    db.refresh(lead)
    return log

