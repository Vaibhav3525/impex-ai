"""
Day 12 — 11-Class Buyer Reply Intelligence & Entity Extraction Engine
PRD §8 & §10: Classifies incoming international buyer inquiries, detects purchasing intent,
extracts quantities, target prices, delivery ports, payment methods, and routes to appropriate CRM pipeline stages.
"""

from __future__ import annotations
import re
from typing import Optional, Dict, Any, Tuple
from app.schemas.reply import ClassificationResult, REPLY_CLASSES

# ─────────────────────────────────────────────────────────────────────────────
# Intent Patterns
# ─────────────────────────────────────────────────────────────────────────────

SCAM_PATTERNS = [
    "advance fee", "tender fee", "registration fee", "western union",
    "lottery", "urgent transfer", "diplomatic delivery", "pay fee first",
    "ministry approval fee", "foreign exchange clearance fee"
]

WRONG_CONTACT_PATTERNS = [
    "wrong email", "wrong person", "no longer with", "left the company",
    "not responsible for", "forwarded to", "contact our purchasing department at",
    "please email our buyer", "wrong department"
]

NOT_INTERESTED_PATTERNS = [
    "unsubscribe", "not interested", "remove us", "do not contact",
    "stop sending", "please remove", "no requirement at this time",
    "we do not buy", "we have existing supplier"
]

SAMPLES_PATTERNS = [
    "send sample", "courier sample", "sample dispatch", "sample evaluation",
    "sample kit", "courier address for sample", "lab sample", "test sample",
    "dispatch 1kg", "can you send sample"
]

SPECS_PATTERNS = [
    "certificate of analysis", "coa", "specification sheet", "spec sheet",
    "lab test", "technical data sheet", "mrl report", "pesticide residue",
    "aflatoxin", "moisture content", "grain length certificate"
]

PRICE_NEGOTIATION_PATTERNS = [
    "too expensive", "counter offer", "discount", "price is high",
    "target price is", "can you offer at", "budget is", "competitor is offering",
    "best price", "lower your price", "target is usd"
]

PAYMENT_TERMS_PATTERNS = [
    "payment terms", "open account", "cad", "da 60", "da 90",
    "letter of credit", "lc at sight", "payment against document",
    "advance payment", "irrevocable lc", "usance lc", "30 days credit"
]

RFQ_PATTERNS = [
    "quote us", "quotation for", "send quotation", "rfq", "price quote",
    "inquire price for", "cif price to", "fob price for", "cif quotation",
    "send proforma", "formal offer"
]

FUTURE_PATTERNS = [
    "next quarter", "next year", "harvest season", "later in the year",
    "keep on file", "touch base in", "future tender", "contract cycle begins",
    "contact us in"
]

INTERESTED_PATTERNS = [
    "interested in your", "pleased to connect", "we are importing",
    "looking for reliable supplier", "send catalog", "can we schedule a call",
    "we distribute", "we import", "sounds promising"
]

MAJOR_PORTS = [
    "Hamburg", "Rotterdam", "Antwerp", "Jebel Ali", "Dubai", "Dammam",
    "Jeddah", "Riyadh", "Tokyo", "Yokohama", "Kobe", "Felixstowe",
    "Southampton", "Marseille", "Le Havre", "Genoa", "Valencia",
    "Barcelona", "New York", "Long Beach", "Los Angeles", "Singapore",
    "Port Klang", "Busan", "Alexandria"
]


# ─────────────────────────────────────────────────────────────────────────────
# Entity Extraction Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_quantity(text: str) -> Optional[str]:
    pattern = r"\b(\d+[\d,\.]*)\s*(MT|metric tons?|tons?|containers?|FCL|bags?|kg|cartons?)\b"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} {match.group(2).upper()}"
    return None

def _extract_target_price(text: str) -> Optional[float]:
    # 1. Prefer explicit target price indicator
    target_pattern = r"(?:target(?: price)?(?: is)?|budget is|offer at)\s*(?:USD|\$|EUR|€)?\s*(\d+[\d,\.]*)"
    m_tgt = re.search(target_pattern, text, re.IGNORECASE)
    if m_tgt:
        try:
            val = float(m_tgt.group(1).replace(",", ""))
            if 10.0 <= val <= 100000.0:
                return val
        except ValueError:
            pass

    # 2. General currency pattern fallback
    patterns = [
        r"(?:USD|\$|EUR|€)\s*(\d+[\d,\.]*)",
        r"(\d+[\d,\.]*)\s*(?:USD|\$|EUR|€|per MT|/MT)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            clean_num = m.group(1).replace(",", "")
            try:
                val = float(clean_num)
                if 10.0 <= val <= 100000.0:
                    return val
            except ValueError:
                pass
    return None

def _extract_delivery_port(text: str) -> Optional[str]:
    for port in MAJOR_PORTS:
        if re.search(rf"\b{re.escape(port)}\b", text, re.IGNORECASE):
            return port
    return None

def _extract_payment_method(text: str) -> Optional[str]:
    text_lower = text.lower()
    if "lc at sight" in text_lower or "letter of credit at sight" in text_lower:
        return "100% Irrevocable LC at Sight"
    elif "lc" in text_lower or "letter of credit" in text_lower:
        return "Letter of Credit (LC)"
    elif "open account" in text_lower:
        return "Open Account (Credit)"
    elif "advance" in text_lower or "tt" in text_lower or "wire transfer" in text_lower:
        return "Wire Transfer (Advance + BL)"
    elif "cad" in text_lower or "cash against documents" in text_lower:
        return "Cash Against Documents (CAD)"
    return None

def _extract_product(text: str) -> Optional[str]:
    keywords = [
        "basmati rice", "sella rice", "raw rice", "non-basmati rice",
        "cardamom", "black pepper", "turmeric", "ginger", "cumin",
        "organic spices", "chili", "chilli", "pulses", "wheat", "maize"
    ]
    text_lower = text.lower()
    for kw in keywords:
        if kw in text_lower:
            return kw.title()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Master Classifier
# ─────────────────────────────────────────────────────────────────────────────

def classify_buyer_reply(subject: str, raw_body: str) -> ClassificationResult:
    """
    Evaluates incoming response from a buyer and extracts structured business entities.
    Determines recommended CRM pipeline progression.
    """
    combined = f"{subject} {raw_body}".lower()

    classification = "Requires Human Review"
    confidence = 0.60
    suggested_stage = "Buyer Replied"

    # Precedence hierarchy: Safety First
    if any(p in combined for p in SCAM_PATTERNS):
        classification = "Potential Scam"
        confidence = 0.95
        suggested_stage = "Lost / Rejected"
    elif any(p in combined for p in NOT_INTERESTED_PATTERNS):
        classification = "Not Interested"
        confidence = 0.92
        suggested_stage = "Lost / Rejected"
    elif any(p in combined for p in WRONG_CONTACT_PATTERNS):
        classification = "Wrong Contact"
        confidence = 0.88
        suggested_stage = "Contacted"
    elif any(p in combined for p in SAMPLES_PATTERNS):
        classification = "Samples"
        confidence = 0.90
        suggested_stage = "Requirements Received"
    elif any(p in combined for p in RFQ_PATTERNS):
        classification = "Request for Quotation"
        confidence = 0.90
        suggested_stage = "Requirements Received"
    elif any(p in combined for p in SPECS_PATTERNS):
        classification = "Request for Specs"
        confidence = 0.85
        suggested_stage = "Requirements Received"
    elif any(p in combined for p in PRICE_NEGOTIATION_PATTERNS):
        classification = "Price Negotiation"
        confidence = 0.85
        suggested_stage = "Negotiation"
    elif any(p in combined for p in PAYMENT_TERMS_PATTERNS):
        classification = "Payment Terms"
        confidence = 0.82
        suggested_stage = "Negotiation"
    elif any(p in combined for p in FUTURE_PATTERNS):
        classification = "Future Requirement"
        confidence = 0.80
        suggested_stage = "Contacted"
    elif any(p in combined for p in INTERESTED_PATTERNS):
        classification = "Interested Buyer"
        confidence = 0.85
        suggested_stage = "Buyer Replied"

    # Extract Entities
    ext_product = _extract_product(raw_body)
    ext_qty = _extract_quantity(raw_body)
    ext_price = _extract_target_price(raw_body)
    ext_port = _extract_delivery_port(raw_body)
    ext_pay = _extract_payment_method(raw_body)

    # Derive Next Action Recommendation
    if classification == "Potential Scam":
        next_action = "Security Alert: Flag and block sender; do not engage."
    elif classification == "Request for Quotation":
        port_note = f" for {ext_port}" if ext_port else ""
        next_action = f"Sales Desk: Prepare formal CIF/FOB proforma quotation{port_note}."
    elif classification == "Samples":
        next_action = "Operations: Dispatch representative courier sample kit with CoA."
    elif classification == "Request for Specs":
        next_action = "Technical Desk: Provide CoA, lab test report, and EU/US MRL compliance sheet."
    elif classification == "Price Negotiation":
        price_note = f" target {ext_price}" if ext_price else ""
        next_action = f"Commercial Desk: Review margin and evaluate counter-offer{price_note}."
    elif classification == "Payment Terms":
        next_action = "Finance Desk: Review requested payment security terms with bank."
    elif classification == "Future Requirement":
        next_action = "CRM: Schedule follow-up calendar reminder for next purchasing cycle."
    elif classification == "Wrong Contact":
        next_action = "Directory: Update lead record with designated procurement contact."
    elif classification == "Not Interested":
        next_action = "Suppression: Record opt-out and suppress from future campaigns."
    elif classification == "Interested Buyer":
        next_action = "Sales Desk: Send product catalog and schedule introductory call."
    else:
        next_action = "Human Review: Inspect message context and assign to sales representative."

    return ClassificationResult(
        classification=classification,
        confidence_score=confidence,
        extracted_product=ext_product,
        extracted_quantity=ext_qty,
        extracted_target_price=ext_price,
        extracted_delivery_port=ext_port,
        extracted_payment_method=ext_pay,
        extracted_next_action=next_action,
        suggested_pipeline_stage=suggested_stage,
    )
