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
    """
    Evaluates commercial deal terms against buyer identity standing and payment risks.
    
    PRD Rule: High-risk transactions require explicit human approval and cannot proceed
    under automated workflows without compliance signoff.
    """
    terms = (deal.payment_terms or "").lower().strip()
    order_val = deal.confirmed_order_value or deal.quotation_amount or 0.0
    lead_risk_score = lead.payment_risk_score or 0.0
    lead_risk_level = lead.risk_level or "LOW"

    risk_factors = []
    status = "Under Review"
    risk_rating = "MEDIUM"
    human_approval_required = True

    # 1. Critical Fraud Flag Check
    if lead_risk_level == "CRITICAL" or "FLAG_ADVANCE_FEE_SCAM" in (lead.risk_flags or []):
        status = "Blocked"
        risk_rating = "CRITICAL"
        risk_factors.append("Buyer flagged with CRITICAL identity/scam pattern on record.")
        rec = "DO NOT SHIP. Reject order and escalate to legal compliance."
        return {
            "deal_id": deal.deal_id,
            "status": status,
            "risk_rating": risk_rating,
            "risk_factors": risk_factors,
            "human_approval_required": True,
            "recommended_action": rec,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    # 2. High-Risk Payment Structure (Unsecured Open Account / DA)
    if any(k in terms for k in HIGH_RISK_TRADE_TERMS):
        status = "Blocked"
        risk_rating = "HIGH"
        risk_factors.append(f"Unsecured payment structure detected: '{deal.payment_terms}'. High non-payment risk for new international buyer.")
        rec = "Insist on 100% Irrevocable LC at Sight or minimum 30% Advance + 70% against BL scan. Never grant open account on first transaction."

    # 3. Secure Terms (Advance or Confirmed LC)
    elif any(k in terms for k in SECURE_PAYMENT_TERMS):
        status = "Approved"
        risk_rating = "LOW"
        human_approval_required = False
        risk_factors.append(f"Highly secured payment term: '{deal.payment_terms}'. Exporter capital fully protected.")
        rec = "Approved for execution. Proceed with packaging and production once funds / LC confirmation is verified with advising bank."

    # 4. Standard Export Terms (LC at Sight / 30% Advance)
    elif any(k in terms for k in STANDARD_TRADE_TERMS):
        if lead.verification_status == "Verified" and lead_risk_score < 30.0:
            status = "Approved"
            risk_rating = "LOW"
            human_approval_required = False
            risk_factors.append("Standard export payment terms accepted for verified corporate buyer.")
            rec = "Standard commercial approval. Dispatch bill of lading through bank upon container boarding."
        else:
            status = "Under Review"
            risk_rating = "MEDIUM"
            human_approval_required = True
            risk_factors.append("Buyer is not fully verified or carries moderate identity flags.")
            rec = "Require trade credit insurance (ECGC India) or request issuing bank pre-advising before dispatch."

    # 5. Unspecified or Ambiguous Terms
    else:
        status = "Flagged"
        risk_rating = "MEDIUM"
        risk_factors.append("Payment terms unspecified or non-standard.")
        rec = "Clarify agreed Incoterms and payment instrument in formal proforma invoice."

    # Order Value Exposure Check
    if order_val > 100000.0:
        risk_factors.append(f"Large capital exposure: USD {order_val:,.2f}. Mandatory management review.")
        if status == "Approved" and "confirmed" not in terms and "100% advance" not in terms:
            human_approval_required = True

    return {
        "deal_id": deal.deal_id,
        "status": status,
        "risk_rating": risk_rating,
        "risk_factors": risk_factors,
        "human_approval_required": human_approval_required,
        "recommended_action": rec,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

def audit_and_save_deal_risk(db: Session, deal: Deal, lead: Lead) -> Dict[str, Any]:
    """Assesses financial risk and saves payment_risk_status and notes to Deal record."""
    assessment = assess_deal_financial_risk(deal, lead)
    deal.payment_risk_status = assessment["status"]
    deal.payment_risk_notes = f"[{assessment['risk_rating']} RISK]: {assessment['recommended_action']} | Factors: {', '.join(assessment['risk_factors'])}"
    db.commit()
    db.refresh(deal)
    return assessment

