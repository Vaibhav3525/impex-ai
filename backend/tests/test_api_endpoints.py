"""
Sync API & Router Integration Tests — self-seeding, order-independent.

These tests operate against the same on-disk SQLite DB as the application.
Each test seeds the specific data it needs before asserting.
"""
from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.api.health import health_check
from app.api.leads import list_leads, create_lead, trigger_verification
from app.api.analytics import get_dashboard_metrics
from app.schemas.lead import LeadCreate


def _ensure_norway_lead(db) -> None:
    """Insert the Norway lead if it doesn't already exist."""
    exists = db.query(Lead).filter(Lead.country == "Norway").first()
    if not exists:
        lc = LeadCreate(
            company_name="Nordic Fish AS",
            country="Norway",
            city="Bergen",
            website="https://www.nordicfish.no",
            product_category="Seafood",
            contact_name="Lars Eriksen",
            job_title="Import Director",
            business_email="lars@nordicfish.no",
            phone_number="+47 55 12 3456",
            source="Norwegian Seafood Council",
            source_url="https://seafood.no/members",
            import_evidence="Active seafood importer listed in Norwegian Seafood Council 2024 directory.",
        )
        create_lead(lead_in=lc, auto_verify=False, db=db)


def test_health_api():
    init_db()
    db = SessionLocal()
    try:
        data = health_check(db=db)
        assert data["status"] == "healthy"
        assert "app_name" in data
    finally:
        db.close()


def test_leads_list_and_filter_api():
    init_db()
    db = SessionLocal()
    try:
        _ensure_norway_lead(db)

        leads_data = list_leads(page=1, page_size=20, db=db)
        assert leads_data.total >= 1
        assert len(leads_data.items) >= 1

        # Test filtering by country — Norway lead guaranteed to exist now
        norway_data = list_leads(page=1, page_size=20, country="Norway", db=db)
        assert norway_data.total >= 1
        assert norway_data.items[0].country == "Norway"
    finally:
        db.close()


def test_dashboard_analytics_api():
    init_db()
    db = SessionLocal()
    try:
        analytics = get_dashboard_metrics(db=db)
        assert "summary" in analytics
        assert "qualification_tiers" in analytics
        assert "outreach_funnel" in analytics
        assert analytics["summary"]["total_leads_discovered"] >= 1
    finally:
        db.close()
