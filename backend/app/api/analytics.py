from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.lead import Lead
from app.models.deal import Deal

router = APIRouter(prefix="/analytics", tags=["Dashboard & Analytics"])

@router.get("/dashboard")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Aggregate primary KPI metrics for the Admin Performance Dashboard."""
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    verified_leads = db.query(func.count(Lead.id)).filter(Lead.verification_status == "Verified").scalar() or 0
    partially_verified = db.query(func.count(Lead.id)).filter(Lead.verification_status == "Partially Verified").scalar() or 0
    unverified_leads = db.query(func.count(Lead.id)).filter(Lead.verification_status == "Unverified").scalar() or 0
    
    # Qualification Tiers
    high_priority = db.query(func.count(Lead.id)).filter(Lead.buyer_score >= 80.0).scalar() or 0
    potential_candidates = db.query(func.count(Lead.id)).filter(Lead.buyer_score >= 60.0, Lead.buyer_score < 80.0).scalar() or 0
    low_priority = db.query(func.count(Lead.id)).filter(Lead.buyer_score < 60.0).scalar() or 0
    
    # Outreach status breakdown
    not_contacted = db.query(func.count(Lead.id)).filter(Lead.outreach_status == "Not Contacted").scalar() or 0
    queued = db.query(func.count(Lead.id)).filter(Lead.outreach_status == "Queued").scalar() or 0
    sent = db.query(func.count(Lead.id)).filter(Lead.outreach_status == "Sent").scalar() or 0
    replied = db.query(func.count(Lead.id)).filter(Lead.outreach_status == "Replied").scalar() or 0

    # Top Countries
    top_countries = (
        db.query(Lead.country, func.count(Lead.id).label("count"))
        .group_by(Lead.country)
        .order_by(func.count(Lead.id).desc())
        .limit(5)
        .all()
    )

    # Top Products
    top_products = (
        db.query(Lead.product_category, func.count(Lead.id).label("count"))
        .group_by(Lead.product_category)
        .order_by(func.count(Lead.id).desc())
        .limit(5)
        .all()
    )

    return {
        "summary": {
            "total_leads_discovered": total_leads,
            "verified_candidates": verified_leads,
            "partially_verified": partially_verified,
            "unverified": unverified_leads,
            "verification_rate_pct": round((verified_leads / total_leads * 100), 1) if total_leads > 0 else 0.0,
        },
        "qualification_tiers": {
            "high_priority_80_100": high_priority,
            "potential_candidates_60_79": potential_candidates,
            "low_priority_below_60": low_priority,
        },
        "outreach_funnel": {
            "not_contacted": not_contacted,
            "queued_for_approval": queued,
            "emails_sent": sent,
            "replies_received": replied,
            "reply_rate_pct": round((replied / sent * 100), 1) if sent > 0 else 0.0,
        },
        "top_countries": [{"country": c[0], "count": c[1]} for c in top_countries],
        "top_products": [{"product": p[0], "count": p[1]} for p in top_products],
    }
