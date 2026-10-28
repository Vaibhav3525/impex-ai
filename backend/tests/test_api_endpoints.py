"""
Sync API & Router Integration Tests
"""
from app.core.database import SessionLocal
from app.api.health import health_check
from app.api.leads import list_leads, create_lead, trigger_verification
from app.api.analytics import get_dashboard_metrics
from app.schemas.lead import LeadCreate

def test_health_api():
    db = SessionLocal()
    try:
        data = health_check(db=db)
        assert data["status"] == "healthy"
        assert "app_name" in data
    finally:
        db.close()

def test_leads_list_and_filter_api():
    db = SessionLocal()
    try:
        leads_data = list_leads(page=1, page_size=20, db=db)
        assert leads_data.total >= 1
        assert len(leads_data.items) >= 1

        # Test filtering by country
        norway_data = list_leads(page=1, page_size=20, country="Norway", db=db)
        assert norway_data.total >= 1
        assert norway_data.items[0].country == "Norway"
    finally:
        db.close()

def test_dashboard_analytics_api():
    db = SessionLocal()
    try:
        analytics = get_dashboard_metrics(db=db)
        assert "summary" in analytics
        assert "qualification_tiers" in analytics
        assert "outreach_funnel" in analytics
        assert analytics["summary"]["total_leads_discovered"] >= 1
    finally:
        db.close()
