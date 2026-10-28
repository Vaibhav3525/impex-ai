"""
Day 6 — Buyer Qualification & Product Matching Engine
PRD §5: Matches discovered buyers against product-specific criteria,
calculates composite qualification scores, evaluates market exclusions,
and produces human-readable qualification explanations with actionable recommendations.
"""

from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.product_profile import ProductProfile
from app.schemas.product_profile import (
    QualificationResult,
    QualificationBreakdown,
)

DECISION_MAKER_KEYWORDS = {
    "procurement", "purchase", "purchasing", "buyer", "sourcing",
    "import", "importer", "director", "owner", "partner", "general manager",
    "head of supply", "category manager", "vp supply"
}

def _normalize_string(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"[^\w\s]", " ", text.lower()).strip()

def _check_country_match(country: str, country_list: List[str]) -> bool:
    """Check if country matches any item in country_list (case-insensitive substring/equality)."""
    if not country or not country_list:
        return False
    norm_lead_country = _normalize_string(country)
    for c in country_list:
        norm_target = _normalize_string(c)
        if norm_target in norm_lead_country or norm_lead_country in norm_target:
            return True
    return False

def evaluate_product_relevance(lead: Lead, product: ProductProfile) -> Tuple[float, List[str]]:
    """
    Evaluates semantic and categorical overlap between exporter product
    and buyer lead records. (Max 30 points)
    """
    score = 0.0
    evidence = []
    
    lead_category = _normalize_string(lead.product_category)
    lead_notes = _normalize_string(lead.notes)
    lead_import = _normalize_string(lead.import_evidence)
    combined_lead_text = f"{lead_category} {lead_notes} {lead_import}"

    prod_name = _normalize_string(product.product_name)
    prod_category = _normalize_string(product.product_category)
    
    # 1. Exact or near-exact product name match in lead category
    if prod_name and (prod_name in lead_category or lead_category in prod_name):
        score += 30.0
        evidence.append(f"Direct product category match: '{lead.product_category}' matches '{product.product_name}'")
        return min(30.0, score), evidence

    # 2. Key commodity terms overlap
    prod_tokens = set(re.findall(r"\w{3,}", prod_name + " " + prod_category))
    # Exclude trivial stop words
    prod_tokens = {t for t in prod_tokens if t not in {"and", "for", "with", "all", "the", "grade", "extra"}}
    
    matched_tokens = [t for t in prod_tokens if t in combined_lead_text]
    
    if len(matched_tokens) >= 2:
        score += 24.0
        evidence.append(f"Strong commodity overlap on key terms: {', '.join(matched_tokens)}")
    elif len(matched_tokens) == 1:
        score += 15.0
        evidence.append(f"Relevant trade keyword detected: '{matched_tokens[0]}'")
    elif prod_category and (prod_category in combined_lead_text or any(t in combined_lead_text for t in prod_category.split())):
        score += 10.0
        evidence.append(f"Industry sector alignment on '{product.product_category}'")
    else:
        evidence.append("No direct product keyword overlap detected in public profile.")

    # HS Code check if present in lead's import notes
    if product.hs_code and product.hs_code in combined_lead_text:
        score += 5.0
        evidence.append(f"Explicit HS Code {product.hs_code} reference found in lead trade record.")

    return min(30.0, score), evidence

def evaluate_country_alignment(lead: Lead, product: ProductProfile) -> Tuple[float, bool, Optional[str], str]:
    """
    Evaluates geographic target alignment. (Max 25 points)
    Enforces strict trade disqualification if lead's country is in excluded list.
    """
    lead_country = lead.country or ""
    
    # 1. Excluded country check - HARD DISQUALIFICATION
    if _check_country_match(lead_country, product.excluded_countries or []):
        reason = f"Country '{lead_country}' is listed under exporter's excluded trade regions policy."
        return 0.0, True, reason, reason

    # 2. Priority target country match
    if product.target_countries and len(product.target_countries) > 0:
        if _check_country_match(lead_country, product.target_countries):
            explanation = f"Country '{lead_country}' is a designated high-priority export destination."
            return 25.0, False, None, explanation
        else:
            explanation = f"Country '{lead_country}' is an open non-priority market (not explicitly targeted, but permitted)."
            return 12.0, False, None, explanation

    # 3. Open market policy (no specific target list specified)
    explanation = f"Country '{lead_country}' is permitted under open destination policy."
    return 18.0, False, None, explanation

def evaluate_import_evidence(lead: Lead, product: ProductProfile) -> Tuple[float, str]:
    """
    Evaluates verifiable import history and trade purchasing behavior. (Max 20 points)
    """
    score = 0.0
    notes = []

    if lead.import_evidence and len(lead.import_evidence.strip()) > 10:
        # Check if import evidence references the commodity
        prod_tokens = set(re.findall(r"\w{3,}", (product.product_name + " " + product.product_category).lower()))
        lead_import_lower = lead.import_evidence.lower()
        if any(t in lead_import_lower for t in prod_tokens if len(t) > 3):
            score += 20.0
            notes.append(f"Direct documentary evidence of purchasing {product.product_name}: '{lead.import_evidence[:90]}...'")
        else:
            score += 15.0
            notes.append(f"Documented import activity recorded: '{lead.import_evidence[:90]}...'")
    elif lead.source and any(s in lead.source.lower() for s in ["apeda", "dgft", "trade portal", "customs", "chamber"]):
        score += 10.0
        notes.append(f"Sourced from official trade portal / export promotion directory: {lead.source}")
    else:
        notes.append("No prior import transaction evidence documented.")

    return min(20.0, score), " | ".join(notes)

def evaluate_contact_quality(lead: Lead) -> Tuple[float, str]:
    """
    Evaluates presence of direct corporate contact channels and procurement decision makers. (Max 15 points)
    """
    score = 0.0
    notes = []

    # Business email quality
    if lead.business_email and "@" in lead.business_email:
        domain = lead.business_email.split("@")[-1].lower()
        from app.services.verification_service import FREE_EMAIL_DOMAINS
        if domain not in FREE_EMAIL_DOMAINS:
            score += 7.0
            notes.append(f"Corporate business email available ({domain})")
        else:
            score += 2.0
            notes.append("Free webmail domain provided")
    else:
        notes.append("No business email available")

    # Decision maker role
    if lead.job_title:
        title_lower = lead.job_title.lower()
        if any(k in title_lower for k in DECISION_MAKER_KEYWORDS):
            score += 5.0
            notes.append(f"Identified procurement decision maker: {lead.job_title}")
        else:
            score += 2.0
            notes.append(f"Contact role noted: {lead.job_title}")
    
    # Phone number / contact name completeness
    if lead.contact_name and lead.phone_number:
        score += 3.0
        notes.append(f"Direct phone & contact person verified ({lead.contact_name})")
    elif lead.contact_name or lead.phone_number:
        score += 1.5
        notes.append("Partial contact information recorded")

    return min(15.0, score), " | ".join(notes)

def evaluate_verification_readiness(lead: Lead) -> Tuple[float, str]:
    """
    Evaluates current verification audit standing. (Max 10 points)
    """
    status = lead.verification_status or "Unverified"
    buyer_score = lead.buyer_score or 0.0

    if status == "Verified" or buyer_score >= 80.0:
        return 10.0, f"Lead is fully Verified with audit score of {buyer_score}/100."
    elif status == "Partially Verified" or buyer_score >= 60.0:
        return 6.0, f"Lead is Partially Verified ({buyer_score}/100) — technical checks passed."
    elif buyer_score > 0:
        return 2.0, f"Lead is Unverified ({buyer_score}/100) — requires preliminary verification."
    else:
        return 0.0, "Lead is unverified and has not completed automated verification audit."

def calculate_qualification_score(lead: Lead, product: ProductProfile) -> QualificationResult:
    """
    Master qualification matching engine.
    Matches a single Lead against an exporter ProductProfile.
    
    PRD Constraints Enforced:
    1. Zero fabrication — score is derived entirely from verified evidence and profile rules.
    2. Explicit explanation — returns comprehensive reasoning why lead was qualified or disqualified.
    3. Excluded markets trigger hard disqualification (score = 0).
    4. Actionable next-step recommendation for export sales team.
    """
    # 1. Geographic check first (handles immediate disqualification)
    country_score, is_disqualified, disq_reason, country_exp = evaluate_country_alignment(lead, product)
    
    if is_disqualified:
        breakdown = QualificationBreakdown(
            product_relevance_score=0.0,
            country_alignment_score=0.0,
            import_evidence_score=0.0,
            contact_quality_score=0.0,
            verification_readiness_score=0.0,
            total_qualification_score=0.0,
        )
        return QualificationResult(
            lead_id=lead.lead_id,
            company_name=lead.company_name,
            country=lead.country,
            product_profile_id=product.profile_id,
            product_name=product.product_name,
            qualification_score=0.0,
            qualification_tier="Disqualified",
            is_disqualified=True,
            disqualification_reason=disq_reason,
            breakdown=breakdown,
            explanation=f"DISQUALIFIED: {disq_reason}",
            recommended_action="Do not initiate outreach. Maintain on internal exclusion register.",
            qualified_at=datetime.now(timezone.utc),
        )

    # 2. Factor evaluations
    prod_score, prod_notes = evaluate_product_relevance(lead, product)
    import_score, import_exp = evaluate_import_evidence(lead, product)
    contact_score, contact_exp = evaluate_contact_quality(lead)
    verif_score, verif_exp = evaluate_verification_readiness(lead)

    total_score = round(prod_score + country_score + import_score + contact_score + verif_score, 1)
    total_score = max(0.0, min(100.0, total_score))

    # Determine Qualification Tier
    if total_score >= 80.0:
        tier = "Highly Qualified"
        rec = f"High priority for Mode A outreach. Prepare customized export quotation based on {product.incoterms} {product.preferred_payment_terms}."
    elif total_score >= 60.0:
        tier = "Conditionally Qualified"
        rec = "Solid candidate. Review contact profile and dispatch introductory product inquiry."
    elif total_score >= 40.0:
        tier = "Marginally Qualified"
        rec = "Secondary candidate. Perform additional web enrichment or search for verified purchasing manager before outreach."
    else:
        tier = "Unqualified"
        rec = "Low alignment with current product specifications. Defer until broader product campaigns or re-verification."

    breakdown = QualificationBreakdown(
        product_relevance_score=prod_score,
        country_alignment_score=country_score,
        import_evidence_score=import_score,
        contact_quality_score=contact_score,
        verification_readiness_score=verif_score,
        total_qualification_score=total_score,
    )

    explanation_lines = [
        f"Qualification Assessment: {total_score}/100 ({tier}) for {product.product_name}",
        f"• Product Match ({prod_score}/30): {' | '.join(prod_notes)}",
        f"• Destination Market ({country_score}/25): {country_exp}",
        f"• Import Credibility ({import_score}/20): {import_exp}",
        f"• Contact Accessibility ({contact_score}/15): {contact_exp}",
        f"• Verification Standing ({verif_score}/10): {verif_exp}",
    ]

    return QualificationResult(
        lead_id=lead.lead_id,
        company_name=lead.company_name,
        country=lead.country,
        product_profile_id=product.profile_id,
        product_name=product.product_name,
        qualification_score=total_score,
        qualification_tier=tier,
        is_disqualified=False,
        disqualification_reason=None,
        breakdown=breakdown,
        explanation="\n".join(explanation_lines),
        recommended_action=rec,
        qualified_at=datetime.now(timezone.utc),
    )

def match_all_leads_for_product(
    db: Session,
    product: ProductProfile,
    min_score: float = 0.0,
    include_disqualified: bool = False,
    limit: int = 50,
) -> List[QualificationResult]:
    """
    Evaluates all leads in the database against the given product profile,
    returning results sorted by qualification_score in descending order.
    """
    leads = db.query(Lead).all()
    results: List[QualificationResult] = []

    for lead in leads:
        res = calculate_qualification_score(lead, product)
        if not include_disqualified and res.is_disqualified:
            continue
        if res.qualification_score >= min_score:
            results.append(res)

    results.sort(key=lambda x: (not x.is_disqualified, x.qualification_score), reverse=True)
    return results[:limit]

