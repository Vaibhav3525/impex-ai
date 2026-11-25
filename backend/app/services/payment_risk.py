"""
Day 13 — Transaction Financial Safety & Commercial Payment Risk Engine
PRD §2, §4 & §11: Evaluates deal-level financial terms, exposure vs order size,
guarantees compliance before commercial production/export commitments, and blocks high-risk payment structures.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.deal import Deal

# Term classification by baseline financial security
SECURE_PAYMENT_TERMS = [
    "100% advance", "confirmed lc", "confirmed irrevocable lc",
    "advance wire", "cash before shipment"
]

STANDARD_TRADE_TERMS = [
    "30% advance", "irrevocable lc at sight", "lc at sight",
    "letter of credit", "cad", "cash against documents", "dp", "d/p"
]

HIGH_RISK_TRADE_TERMS = [
    "open account", "oa 30", "oa 60", "oa 90", "da", "d/a",
    "documents against acceptance", "unsecured credit", "payment after delivery"
]

def assess_deal_financial_risk(deal: Deal, lead: Lead) -> Dict[str, Any]:
    import re
    terms = (deal.payment_terms or "").lower().strip()
    risk, status, approval = "MEDIUM", "Under Review", True
    factors = []
    if lead.risk_level == "CRITICAL" or {"FLAG_ADVANCE_FEE_SCAM", "FLAG_UPFRONT_FEE_SOLICITATION"}.intersection(lead.risk_flags or []):
        status, risk = "Blocked", "CRITICAL"
        factors.append("Critical buyer identity or fraud signal.")
    elif re.search(r"\b(?:open\s+account|oa(?:\s*\d+)?|d\s*/\s*a|da|documents\s+against\s+acceptance|unsecured\s+credit|payment\s+after\s+delivery)\b", terms):
        status, risk = "Blocked", "HIGH"
        factors.append("Unsecured buyer credit is blocked.")
    elif re.search(r"\b(?:unconfirmed|unsecured|revocable|not\s+confirmed|no|without|unless)\b", terms):
        factors.append("Terms contain qualifications or negations requiring review.")
    elif re.search(r"(?:100\s*%\s*(?:advance|prepayment)|\badvance\s+wire\b|\bcash\s+before\s+shipment\b|\bconfirmed\s+(?:irrevocable\s+)?(?:lc|letter\s+of\s+credit)\b)", terms):
        status, risk, approval = "Approved", "LOW", False
        factors.append("Advance or confirmed credit terms proposed; bank evidence still required.")
    elif re.search(r"(?:30\s*%\s*advance|\b(?:irrevocable\s+)?lc\s+at\s+sight\b|\bletter\s+of\s+credit\b|\bcad\b|\bcash\s+against\s+documents\b|\bd\s*/\s*p\b|\bdp\b)", terms):
        if lead.verification_status == "Verified" and lead.risk_level == "LOW" and (lead.payment_risk_score or 0) < 30:
            status, risk, approval = "Approved", "LOW", False
        factors.append("Documentary trade terms require bank/document checks.")
    else:
        factors.append("Payment instrument is missing or ambiguous.")
    if status == "Approved" and (lead.verification_status != "Verified" or lead.risk_level != "LOW"):
        status, risk, approval = "Under Review", "MEDIUM", True
        factors.append("Buyer evidence review is incomplete.")
    if (deal.confirmed_order_value or deal.quotation_amount or 0) > 100000:
        approval = True
        factors.append("Large exposure requires an authenticated management review.")
    return {"deal_id": deal.deal_id, "status": status, "risk_rating": risk, "risk_factors": factors, "human_approval_required": approval, "recommended_action": "Verify bank payment or credit instrument and record the evidence before confirming an order." if status != "Blocked" else "Do not confirm or ship. Renegotiate payment terms and resolve buyer risk.", "evaluated_at": datetime.now(timezone.utc).isoformat()}


def enforce_order_confirmation(deal, lead):
    from fastapi import HTTPException
    result = assess_deal_financial_risk(deal, lead)
    if result["status"] != "Approved" or deal.payment_risk_status == "Blocked":
        raise HTTPException(409, "Order confirmation is blocked by the current payment or buyer assessment.")
    if not deal.payment_evidence_reference or not deal.payment_verified_by or not deal.payment_verified_at:
        raise HTTPException(409, "Record authenticated bank/payment evidence before confirming the order.")
    timestamp = deal.payment_verified_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if (datetime.now(timezone.utc) - timestamp).days >= 30:
        raise HTTPException(409, "Payment evidence has expired; review it again.")
    return result


def audit_and_save_deal_risk(db: Session, deal: Deal, lead: Lead) -> Dict[str, Any]:
    """Assesses financial risk and saves payment_risk_status and notes to Deal record."""
    assessment = assess_deal_financial_risk(deal, lead)
    deal.payment_risk_status = assessment["status"]
    deal.payment_risk_notes = f"[{assessment['risk_rating']} RISK]: {assessment['recommended_action']} | Factors: {', '.join(assessment['risk_factors'])}"
    db.commit()
    db.refresh(deal)
    return assessment

