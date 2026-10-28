"""
Day 8 — Payment Risk Guardian & Fraud Detection Service
PRD §4 & §11: Strict separation of Commercial Qualification vs Financial/Payment Risk.
Evaluates potential international buyers for advance-fee scams, third-party payment diversions,
unrealistic first-order demands, domain fraud, and country inconsistencies.
"""

from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.verification import VerificationLog
from app.schemas.lead import RiskAssessmentResponse, RiskSignal
from app.services.verification_service import FREE_EMAIL_DOMAINS

# Known ccTLD to country mapping for inconsistency detection
CCTLD_COUNTRY_MAP = {
    "de": "germany",
    "fr": "france",
    "uk": "united kingdom",
    "it": "italy",
    "es": "spain",
    "nl": "netherlands",
    "jp": "japan",
    "ae": "united arab emirates",
    "sa": "saudi arabia",
    "no": "norway",
    "dk": "denmark",
    "se": "sweden",
    "ca": "canada",
    "au": "australia",
    "us": "united states",
    "in": "india",
    "sg": "singapore",
    "my": "malaysia",
    "br": "brazil",
    "tr": "turkey",
}

ADVANCE_FEE_KEYWORDS = [
    "advance fee", "registration fee", "tender fee", "bid bond fee",
    "issuance fee", "legalization fee", "release fee", "processing fee upfront",
    "pay fee first", "contract registration fee", "ministry approval fee"
]

THIRD_PARTY_PAYMENT_KEYWORDS = [
    "third party payer", "different country bank", "offshore payment",
    "pay via agent", "third party company", "receive from third party",
    "alternate company paying", "payment from another jurisdiction"
]

UNREALISTIC_TERMS_KEYWORDS = [
    "open account 100%", "refuse lc", "no letter of credit",
    "da 120 days", "da 90 days without guarantee", "no advance payment possible"
]

def _check_text_patterns(text: Optional[str], patterns: List[str]) -> Optional[str]:
    """Check if any regex/substring pattern is found in the normalized text."""
    if not text:
        return None
    text_lower = text.lower()
    for p in patterns:
        if p in text_lower:
            return p
    return None

def check_country_tld_mismatch(website: Optional[str], country: Optional[str]) -> Optional[Tuple[str, str]]:
    """
    Checks if a country-code top-level domain contradicts the stated buyer country.
    Returns (tld, mapped_country) if mismatch is detected.
    """
    if not website or not country:
        return None
    
    clean_url = website.lower().strip()
    clean_url = re.sub(r"^https?://", "", clean_url)
    clean_url = re.sub(r"^www\.", "", clean_url)
    domain_part = clean_url.split("/")[0].split(":")[0]
    
    # Check if domain has a 2-letter ccTLD
    parts = domain_part.split(".")
    if len(parts) >= 2:
        tld = parts[-1]
        if tld in CCTLD_COUNTRY_MAP:
            expected_country = CCTLD_COUNTRY_MAP[tld]
            norm_country = country.lower().strip()
            # If expected country is not part of stated country
            if expected_country not in norm_country and norm_country not in expected_country:
                return (tld, expected_country)
    return None

def evaluate_lead_payment_risk(lead: Lead) -> RiskAssessmentResponse:
    """
    Performs comprehensive fraud and financial risk audit on a buyer lead.
    
    Invariants:
      1. Zero fabrication — signals must cite exact evidence in lead record.
      2. Clear risk separation — high qualification score never cancels out high risk flags.
      3. CRITICAL risk triggers immediate human approval requirement.
    """
    signals: List[RiskSignal] = []
    total_risk_score = 0.0

    combined_text = f"{lead.company_name} {lead.product_category} {lead.notes or ''} {lead.import_evidence or ''}"

    # 1. Advance Fee Scam Pattern (CRITICAL)
    adv_match = _check_text_patterns(combined_text, ADVANCE_FEE_KEYWORDS)
    if adv_match:
        signals.append(RiskSignal(
            flag="FLAG_ADVANCE_FEE_SCAM",
            severity="CRITICAL",
            points=40.0,
            description="Advance fee or tender registration scam pattern detected in trade notes.",
            evidence=f"Text contains flagged phrase: '{adv_match}'",
        ))
        total_risk_score += 40.0

    # 2. Third-Party Payer Diversion (HIGH)
    tp_match = _check_text_patterns(combined_text, THIRD_PARTY_PAYMENT_KEYWORDS)
    if tp_match:
        signals.append(RiskSignal(
            flag="FLAG_THIRD_PARTY_PAYER",
            severity="HIGH",
            points=25.0,
            description="Buyer indicates payment will originate from an unrelated third party or offshore jurisdiction.",
            evidence=f"Text contains third-party payer indicator: '{tp_match}'",
        ))
        total_risk_score += 25.0

    # 3. Domain Not Found / NXDOMAIN (CRITICAL)
    if "FLAG_DOMAIN_NOT_FOUND" in (lead.risk_flags or []):
        signals.append(RiskSignal(
            flag="FLAG_DOMAIN_NOT_FOUND",
            severity="CRITICAL",
            points=40.0,
            description="Domain failed DNS resolution (NXDOMAIN). The website or email domain does not exist in DNS.",
            evidence="DNS resolver returned NXDOMAIN during technical verification.",
        ))
        total_risk_score += 40.0

    # 4. Free Webmail Domain for International Buyer (HIGH)
    if lead.business_email and "@" in lead.business_email:
        domain = lead.business_email.split("@")[-1].lower().strip()
        if domain in FREE_EMAIL_DOMAINS:
            signals.append(RiskSignal(
                flag="FLAG_FREE_EMAIL_DOMAIN",
                severity="HIGH",
                points=25.0,
                description="International buyer operates via free/disposable webmail provider rather than corporate domain.",
                evidence=f"Email domain '{domain}' is in public free webmail registry.",
            ))
            total_risk_score += 25.0

    # 5. Young Domain (<90 Days Old) (HIGH)
    if "FLAG_DOMAIN_AGE_UNDER_90_DAYS" in (lead.risk_flags or []):
        signals.append(RiskSignal(
            flag="FLAG_DOMAIN_AGE_UNDER_90_DAYS",
            severity="HIGH",
            points=25.0,
            description="Domain was registered less than 90 days ago. Frequently associated with temporary shell entities.",
            evidence="WHOIS creation date is within the last 90 calendar days.",
        ))
        total_risk_score += 25.0

    # 6. Country & Website TLD Mismatch (HIGH)
    tld_mismatch = check_country_tld_mismatch(lead.website, lead.country)
    if tld_mismatch:
        tld, exp_country = tld_mismatch
        signals.append(RiskSignal(
            flag="FLAG_COUNTRY_MISMATCH",
            severity="HIGH",
            points=20.0,
            description=f"Buyer country is stated as '{lead.country}', but official website uses '.{tld}' ({exp_country.title()}).",
            evidence=f"Website '{lead.website}' ccTLD maps to {exp_country.title()}.",
        ))
        total_risk_score += 20.0

    # 7. Unverified / Aggressive Payment Terms (MEDIUM)
    terms_match = _check_text_patterns(combined_text, UNREALISTIC_TERMS_KEYWORDS)
    if terms_match:
        signals.append(RiskSignal(
            flag="FLAG_UNVERIFIED_PAYMENT_TERMS",
            severity="MEDIUM",
            points=15.0,
            description="Buyer demands unsecured terms or explicitly rejects standard documentary letters of credit.",
            evidence=f"Text indicates restrictive terms: '{terms_match}'",
        ))
        total_risk_score += 15.0

    # 8. Missing Corporate Website (MEDIUM)
    if not lead.website or "FLAG_MISSING_WEBSITE" in (lead.risk_flags or []):
        signals.append(RiskSignal(
            flag="FLAG_MISSING_WEBSITE",
            severity="MEDIUM",
            points=10.0,
            description="Buyer lacks an official corporate website to verify physical location and business identity.",
            evidence="No valid website URL recorded in lead profile.",
        ))
        total_risk_score += 10.0

    # 9. No Direct Import History (LOW)
    if not lead.import_evidence or "FLAG_NO_DIRECT_IMPORT_EVIDENCE" in (lead.risk_flags or []):
        signals.append(RiskSignal(
            flag="FLAG_NO_DIRECT_IMPORT_EVIDENCE",
            severity="LOW",
            points=5.0,
            description="No direct past bill of lading or customs import records on file.",
            evidence="Import evidence field is empty or unverified.",
        ))
        total_risk_score += 5.0

    # Clamp total score 0 to 100
    payment_risk_score = round(max(0.0, min(100.0, total_risk_score)), 1)

    # Determine Risk Level
    severities = {s.severity for s in signals}
    if "CRITICAL" in severities or payment_risk_score >= 70.0:
        risk_level = "CRITICAL"
        requires_approval = True
        safe_for_outreach = False
        summary = f"CRITICAL RISK ({payment_risk_score}/100): High probability of fraudulent operation or severe identity anomaly."
        rec = "DO NOT PROCEED. Reject lead or freeze outreach until full original trade registry documents are verified by senior compliance."
    elif "HIGH" in severities or payment_risk_score >= 40.0:
        risk_level = "HIGH"
        requires_approval = True
        safe_for_outreach = False
        summary = f"HIGH RISK ({payment_risk_score}/100): Significant verification risks detected (e.g. personal email, young domain, or country mismatch)."
        rec = "Manual approval required. Transact exclusively on 100% Confirmed Irrevocable LC at Sight or Advance Wire Transfer. Never grant open account credit."
    elif payment_risk_score >= 20.0:
        risk_level = "MEDIUM"
        requires_approval = False
        safe_for_outreach = True
        summary = f"MEDIUM RISK ({payment_risk_score}/100): Moderate identity gaps, typical of unverified directory listings."
        rec = "Permitted for Mode A assisted outreach. Insist on standard 30% advance + 70% against BL payment security."
    else:
        risk_level = "LOW"
        requires_approval = False
        safe_for_outreach = True
        summary = f"LOW RISK ({payment_risk_score}/100): Clean record with verified corporate identity and no fraud signals."
        rec = "Approved for standard outreach and export negotiation under normal commercial terms."

    return RiskAssessmentResponse(
        lead_id=lead.lead_id,
        company_name=lead.company_name,
        country=lead.country,
        buyer_score=lead.buyer_score or 0.0,
        payment_risk_score=payment_risk_score,
        risk_level=risk_level,
        detected_signals=signals,
        requires_human_approval=requires_approval,
        is_safe_for_automated_outreach=safe_for_outreach,
        summary=summary,
        recommended_mitigation=rec,
        assessed_at=datetime.now(timezone.utc),
    )

def audit_and_save_lead_risk(db: Session, lead: Lead) -> RiskAssessmentResponse:
    """Evaluates risk and persists updated payment_risk_score and risk_level to Lead record."""
    assessment = evaluate_lead_payment_risk(lead)
    
    lead.payment_risk_score = assessment.payment_risk_score
    lead.risk_level = assessment.risk_level
    
    # Merge detected signal flags into lead.risk_flags
    existing_flags = set(lead.risk_flags or [])
    for s in assessment.detected_signals:
        existing_flags.add(s.flag)
    lead.risk_flags = list(existing_flags)

    db.commit()
    db.refresh(lead)
    return assessment

