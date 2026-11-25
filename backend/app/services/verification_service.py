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


def run_lead_verification(db: Session, lead: Lead, enrichment=None, run_live_checks: bool = True) -> VerificationLog:
    """Score reviewed documentary evidence and observed technical checks only.

    Populated fields, source labels and narrative import claims are unreviewed inputs.
    DNS/TLS demonstrate infrastructure, never company identity or mailbox ownership.
    """
    import httpx
    from app.services.evidence_service import current_evidence, usable_source
    evidence = current_evidence(db, lead.lead_id)
    weights = {"identity": 20.0, "relevance": 20.0, "website": 15.0, "email": 15.0, "imports": 15.0, "independent": 15.0}
    scores = {key: value if key in evidence else 0.0 for key, value in weights.items()}
    flags = [f for f in (lead.risk_flags or []) if f in {"FLAG_ADVANCE_FEE_SCAM", "FLAG_UPFRONT_FEE_SOLICITATION", "FLAG_SYNTHETIC_RECORD"}]
    _, email_flags = evaluate_email_quality(lead.business_email)
    flags.extend(email_flags)
    if not usable_source(lead.source_url):
        flags.append("FLAG_UNVERIFIABLE_SOURCE")
    if not evidence:
        flags.append("FLAG_DOCUMENTARY_REVIEW_REQUIRED")
    email_domain = _extract_domain(lead.business_email) if lead.business_email else None
    website_domain = _extract_domain(lead.website) if lead.website else None
    dns_records, ssl_valid, http_status, age = [], None, None, None
    if run_live_checks and _ENRICHMENT_AVAILABLE:
        if email_domain:
            try:
                mx = enrichment.mx if enrichment and enrichment.domain == email_domain else check_dns_mx(email_domain, timeout=4.0)
                if mx and mx.has_mx:
                    dns_records = mx.records
                    scores["email"] = 15.0 if not email_flags else 2.0
                elif mx and "NXDOMAIN" in (mx.error or ""):
                    flags.append("FLAG_DOMAIN_NOT_FOUND")
                    scores["email"] = 0.0
            except Exception:
                flags.append("FLAG_EMAIL_CHECK_INCOMPLETE")
        if usable_source(lead.website):
            try:
                tls = enrichment.tls if enrichment and enrichment.domain == website_domain else check_tls(website_domain)
                ssl_valid = "VALID" if tls and tls.valid else "INVALID"
                if tls and tls.valid:
                    scores["website"] = max(scores["website"], 5.0)
                else:
                    flags.append("FLAG_TLS_INVALID")
                    scores["website"] = 0.0
                response = httpx.get(lead.website, timeout=5.0, follow_redirects=False)
                http_status = response.status_code
                if http_status == 200:
                    scores["website"] = min(scores["website"] + 10.0, 15.0)
            except Exception:
                flags.append("FLAG_WEBSITE_CHECK_INCOMPLETE")
    critical = {"FLAG_ADVANCE_FEE_SCAM", "FLAG_UPFRONT_FEE_SOLICITATION", "FLAG_DOMAIN_NOT_FOUND", "FLAG_SYNTHETIC_RECORD"}
    risk = "CRITICAL" if critical.intersection(flags) else "HIGH" if "FLAG_FREE_EMAIL_DOMAIN" in flags else "MEDIUM" if flags else "LOW"
    total = round(sum(scores.values()), 1)
    status = "Verified" if total >= 80 and risk == "LOW" and {"identity", "imports"}.issubset(evidence) else "Partially Verified" if total >= 60 and risk != "CRITICAL" else "Unverified"
    summary = "Reviewed evidence: " + (", ".join(sorted(evidence)) or "none") + ". Unreviewed profile text contributes no points."
    log = VerificationLog(lead_id=lead.lead_id, identity_score=scores["identity"], relevance_score=scores["relevance"], website_score=scores["website"], email_score=scores["email"], import_evidence_score=scores["imports"], independent_score=scores["independent"], total_score=total, dns_mx_records=dns_records, http_status=http_status, ssl_valid=ssl_valid, risk_level=risk, detected_flags=sorted(set(flags)), verified_by="evidence_engine_v2", evidence_summary=summary)
    db.add(log)
    lead.buyer_score, lead.verification_status, lead.risk_flags = total, status, log.detected_flags
    lead.risk_level = risk
    lead.last_verified = datetime.now(timezone.utc)
    if status == "Verified" and lead.pipeline_stage in {"Discovered", "Verification Pending"}:
        lead.pipeline_stage = "Verified Candidate"
    db.commit()
    db.refresh(lead)
    return log
