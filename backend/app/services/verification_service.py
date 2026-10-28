"""
100-Point Lead Verification Engine.
Evidence-based scoring — no fabrication, no assumptions.

Score Breakdown (PRD §4):
  identity_score      (max 20) — company identity & registration evidence
  relevance_score     (max 20) — product & industry relevance
  website_score       (max 15) — website & business identity consistency
  email_score         (max 15) — business email verification
  import_evidence_score (max 15) — evidence of relevant import/purchasing activity
  independent_score   (max 15) — independent supporting evidence

Classification:
  80–100 : Verified           — high-priority candidate
  60–79  : Partially Verified — requires additional verification
  < 60   : Unverified         — low-priority or insufficient evidence

Risk Levels:
  CRITICAL — advance-fee/scam flags, domain NXDOMAIN
  HIGH     — free email domain or known scam pattern
  MEDIUM   — 2+ minor flags
  LOW      — clean record

Day 5 additions:
  - Integrates live DNS MX lookup via dnspython
  - Integrates TLS certificate check
  - Stores results in VerificationLog columns
  - Accepts pre-computed DomainEnrichmentResult to avoid double network hits
"""

import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.models.verification import VerificationLog

# Domain enrichment is optional — import lazily to avoid hard dependency in tests
try:
    from app.services.domain_enrichment import (
        check_dns_mx,
        check_tls,
        DomainEnrichmentResult,
    )
    _ENRICHMENT_AVAILABLE = True
except ImportError:
    _ENRICHMENT_AVAILABLE = False

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "protonmail.com", "icloud.com", "mail.com", "zoho.com", "yandex.com",
    "tempmail.com", "mailinator.com", "guerrillamail.com", "10minutemail.com",
}


def evaluate_email_quality(email: str | None) -> Tuple[float, List[str]]:
    """
    Checks email domain credibility and flags free or disposable domains.

    Returns:
        (score, flags) where score is 0–15 and flags is a list of FLAG_* strings.
    """
    if not email or "@" not in email:
        return 0.0, ["FLAG_MISSING_EMAIL"]

    domain = email.split("@")[-1].lower().strip()
    flags: List[str] = []

    if domain in FREE_EMAIL_DOMAINS:
        flags.append("FLAG_FREE_EMAIL_DOMAIN")
        return 2.0, flags   # Minimal points for personal/disposable email

    # Valid corporate domain format
    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", domain):
        return 15.0, []     # Full 15 points — domain format OK

    return 5.0, ["FLAG_SUSPICIOUS_EMAIL_SYNTAX"]


def _extract_domain(email_or_url: str) -> Optional[str]:
    """Extract bare domain from an email or URL."""
    s = email_or_url.strip().lower()
    if "@" in s:
        return s.split("@")[-1]
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    return s.split("/")[0] or None


def run_lead_verification(
    db: Session,
    lead: Lead,
    enrichment: Optional["DomainEnrichmentResult"] = None,
    run_live_checks: bool = True,
) -> VerificationLog:
    """
    Execute the 100-point verification model against *lead*.

    Args:
        db:             SQLAlchemy session.
        lead:           The Lead record to verify.
        enrichment:     Pre-computed DomainEnrichmentResult.  If None and
                        run_live_checks is True, basic MX + TLS checks are
                        run here.  Pass enrichment=None and run_live_checks=False
                        for a fast offline-only score (used in tests / batch).
        run_live_checks: Whether to perform live DNS/TLS checks when no
                        pre-computed enrichment is provided.

    Returns:
        VerificationLog saved to the database.

    PRD invariants:
        - Score must reflect available evidence only.
        - Flags must be concrete identifiable risks, not guesses.
        - Never upgrade status without supporting evidence.
    """
    identity_score = 0.0
    relevance_score = 0.0
    website_score = 0.0
    email_score = 0.0
    import_evidence_score = 0.0
    independent_score = 0.0
    detected_flags: List[str] = []
    evidence_parts: List[str] = []

    # ── 1. Company Identity & Registration (Max 20) ───────────────────────
    if lead.company_name and len(lead.company_name.strip()) > 2:
        identity_score += 10.0
        evidence_parts.append(f"Company name present: {lead.company_name}")
    if lead.country and lead.city:
        identity_score += 5.0
        evidence_parts.append(f"Location: {lead.city}, {lead.country}")
    if lead.source and "registry" in lead.source.lower():
        identity_score += 5.0
        evidence_parts.append(f"Source is a registry: {lead.source}")

    # ── 2. Product & Industry Relevance (Max 20) ──────────────────────────
    if lead.product_category and len(lead.product_category.strip()) > 0:
        relevance_score += 12.0
        evidence_parts.append(f"Product category: {lead.product_category}")
    if lead.job_title and any(
        k in lead.job_title.lower()
        for k in ["procurement", "purchase", "buyer", "import", "sourcing", "director", "owner"]
    ):
        relevance_score += 8.0
        evidence_parts.append(f"Relevant job title: {lead.job_title}")

    # ── 3. Website & Business Identity Consistency (Max 15) ───────────────
    if lead.website:
        if lead.website.startswith("http://") or lead.website.startswith("https://"):
            website_score += 8.0
        if "https://" in lead.website:
            website_score += 4.0
        if lead.contact_name:
            website_score += 3.0
        evidence_parts.append(f"Website present: {lead.website}")
    else:
        detected_flags.append("FLAG_MISSING_WEBSITE")

    # ── 4. Business Email Verification (Max 15) ───────────────────────────
    e_score, e_flags = evaluate_email_quality(lead.business_email)
    email_score = e_score
    detected_flags.extend(e_flags)
    if lead.business_email:
        evidence_parts.append(f"Email domain: {lead.business_email.split('@')[-1]}")

    # ── 5. Evidence of Import Activity (Max 15) ───────────────────────────
    if lead.import_evidence and len(lead.import_evidence.strip()) > 10:
        import_evidence_score += 15.0
        evidence_parts.append("Direct import evidence recorded.")
    elif lead.source and any(
        s in lead.source.lower()
        for s in ["apeda", "dgft", "customs", "comtrade", "embassy", "trade portal"]
    ):
        import_evidence_score += 10.0
        evidence_parts.append(f"Source is a trade authority: {lead.source}")
    else:
        detected_flags.append("FLAG_NO_DIRECT_IMPORT_EVIDENCE")

    # ── 6. Independent Supporting Evidence (Max 15) ───────────────────────
    if lead.phone_number:
        independent_score += 5.0
    if lead.source_url:
        independent_score += 5.0
    if lead.contact_name and lead.job_title:
        independent_score += 5.0

    # ── Live Technical Checks (Day 5) ─────────────────────────────────────
    dns_mx_records: List[str] = []
    http_status: Optional[int] = None
    ssl_valid: Optional[str] = None
    domain_age_days: Optional[int] = None

    if _ENRICHMENT_AVAILABLE and run_live_checks and not enrichment:
        # Run minimal live checks inline (MX + TLS only — no WHOIS/contact page here)
        domain = None
        if lead.business_email:
            domain = _extract_domain(lead.business_email)
        elif lead.website:
            domain = _extract_domain(lead.website)

        if domain:
            try:
                mx_result = check_dns_mx(domain, timeout=4.0)
                if mx_result.has_mx:
                    dns_mx_records = mx_result.records
                    email_score = min(email_score + 5.0, 15.0)
                    evidence_parts.append(f"Live MX confirmed: {', '.join(mx_result.records[:2])}")
                elif mx_result.error and "NXDOMAIN" in mx_result.error:
                    detected_flags.append("FLAG_DOMAIN_NOT_FOUND")
                    email_score = max(0.0, email_score - 5.0)
            except Exception:
                pass  # Network unavailable in sandbox — non-fatal

            try:
                tls_result = check_tls(domain)
                if tls_result.valid:
                    ssl_valid = "VALID"
                    website_score = min(website_score + 3.0, 15.0)
                    if tls_result.days_to_expiry is not None:
                        evidence_parts.append(
                            f"TLS valid, {tls_result.days_to_expiry} days to expiry."
                        )
                    if tls_result.days_to_expiry is not None and tls_result.days_to_expiry <= 30:
                        detected_flags.append("FLAG_TLS_EXPIRING_SOON")
                else:
                    ssl_valid = "INVALID"
                    detected_flags.append("FLAG_TLS_INVALID")
            except Exception:
                pass

    elif enrichment:
        # Incorporate pre-computed enrichment results
        email_score = min(
            max(0.0, email_score + enrichment.email_score_delta), 15.0
        )
        website_score = min(
            max(0.0, website_score + enrichment.website_score_delta), 15.0
        )
        independent_score = min(
            max(0.0, independent_score + enrichment.independent_score_delta), 15.0
        )
        detected_flags.extend(enrichment.new_flags)
        evidence_parts.extend(enrichment.evidence_notes)

        if enrichment.mx and enrichment.mx.has_mx:
            dns_mx_records = enrichment.mx.records
        if enrichment.tls:
            ssl_valid = "VALID" if enrichment.tls.valid else "INVALID"
        if enrichment.whois and enrichment.whois.domain_age_days is not None:
            domain_age_days = enrichment.whois.domain_age_days

    # ── Total Score ────────────────────────────────────────────────────────
    total_score = round(
        identity_score + relevance_score + website_score
        + email_score + import_evidence_score + independent_score,
        1,
    )

    # ── Verification Status ────────────────────────────────────────────────
    if total_score >= 80.0 and "FLAG_FREE_EMAIL_DOMAIN" not in detected_flags:
        status = "Verified"
    elif total_score >= 60.0:
        status = "Partially Verified"
    else:
        status = "Unverified"

    # ── Risk Level ────────────────────────────────────────────────────────
    critical_flags = {"FLAG_ADVANCE_FEE_SCAM", "FLAG_DOMAIN_NOT_FOUND"}
    high_flags = {"FLAG_FREE_EMAIL_DOMAIN"}
    if any(f in detected_flags for f in critical_flags):
        risk_level = "CRITICAL"
    elif any(f in detected_flags for f in high_flags):
        risk_level = "HIGH"
    elif len(detected_flags) >= 2:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # ── Persist VerificationLog ────────────────────────────────────────────
    evidence_summary = (
        f"Automated evaluation scored {total_score}/100. "
        f"Status: {status}. Risk: {risk_level}. "
        + " | ".join(evidence_parts[:5])
    )

    log = VerificationLog(
        lead_id=lead.lead_id,
        identity_score=identity_score,
        relevance_score=relevance_score,
        website_score=website_score,
        email_score=email_score,
        import_evidence_score=import_evidence_score,
        independent_score=independent_score,
        total_score=total_score,
        dns_mx_records=dns_mx_records,
        smtp_check_result=None,
        http_status=http_status,
        ssl_valid=ssl_valid,
        domain_age_days=domain_age_days,
        risk_level=risk_level,
        detected_flags=detected_flags,
        evidence_summary=evidence_summary,
    )
    db.add(log)

    # ── Update Lead ────────────────────────────────────────────────────────
    lead.buyer_score = total_score
    lead.verification_status = status
    lead.risk_flags = detected_flags
    lead.last_verified = datetime.now(timezone.utc)
    if status == "Verified" and lead.pipeline_stage == "Discovered":
        lead.pipeline_stage = "Verified Candidate"

    db.commit()
    db.refresh(lead)
    return log
