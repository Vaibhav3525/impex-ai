import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.lead import Lead
from app.api.health import health_check
from app.api.leads import list_leads, create_lead, trigger_verification
from app.api.analytics import get_dashboard_metrics
from app.schemas.lead import LeadCreate

def test_full_suite():
    db = SessionLocal()
    try:
        print("[1] Testing Health Endpoint...", flush=True)
        h = health_check(db=db)
        print("    Health:", h, flush=True)
        assert h["status"] == "healthy"

        print("[2] Testing Lead Listing...", flush=True)
        leads = list_leads(page=1, page_size=20, db=db)
        print(f"    Total Leads: {leads.total}", flush=True)
        assert leads.total >= 4

        print("[3] Testing Lead Ingestion with Verification...", flush=True)
        test_new_lead = LeadCreate(
            company_name="Tokyo Nippon Spices KK",
            country="Japan",
            city="Tokyo",
            website="https://www.nipponspices.example.jp",
            product_category="Organic Spices & Turmeric",
            contact_name="Kenji Sato",
            job_title="Purchasing General Manager",
            business_email="k.sato@nipponspices.example.jp",
            phone_number="+81 3 5555 0199",
            source="Japan Food Importers Association",
            source_url="https://jfia.example.or.jp/members",
            import_evidence="Registered importer of high-grade turmeric under Japan Ministry of Health, Labour and Welfare (MHLW)."
        )
        created = create_lead(lead_in=test_new_lead, auto_verify=True, db=db)
        print(f"    Created: {created.company_name} ({created.lead_id}) | Score: {created.buyer_score} | Status: {created.verification_status}", flush=True)
        assert created.buyer_score >= 80.0
        assert created.verification_status == "Verified"

        print("[4] Testing Analytics Dashboard Aggregates...", flush=True)
        dash = get_dashboard_metrics(db=db)
        print("    Total Discovered:", dash["summary"]["total_leads_discovered"], flush=True)
        print("    Verification Rate:", dash["summary"]["verification_rate_pct"], "%", flush=True)
        print("    High Priority Buyers (80-100):", dash["qualification_tiers"]["high_priority_80_100"], flush=True)
        print("    Top Countries:", [c["country"] for c in dash["top_countries"]], flush=True)
        assert dash["summary"]["total_leads_discovered"] >= 5

        print("\n[SUCCESS] ALL BACKEND CORE CAPABILITIES AND APIS 100% OPERATIONAL!", flush=True)
    finally:
        db.close()

if __name__ == "__main__":
    test_full_suite()
