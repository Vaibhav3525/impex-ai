import sys, asyncio
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import SessionLocal
from app.models.lead import Lead
from app.api.health import health_check
from app.api.leads import list_leads
from app.api.analytics import get_dashboard_metrics

async def run_all():
    print("[1] Opening database session...", flush=True)
    db = SessionLocal()
    try:
        print("[2] Testing Health Endpoint...", flush=True)
        health = await health_check(db=db)
        print(f"    Health Status: {health['status']} | Database: {health['database']}", flush=True)
        assert health["status"] == "healthy"

        print("[3] Testing Lead Listing...", flush=True)
        leads_res = await list_leads(page=1, page_size=20, db=db)
        print(f"    Total Leads Ingested: {leads_res.total}", flush=True)
        for lead in leads_res.items:
            print(f"    * [{lead.verification_status}] {lead.company_name} ({lead.country}) | Score: {lead.buyer_score}/100", flush=True)
        assert leads_res.total >= 4

        print("[4] Testing Lead Filtering by Country (Norway)...", flush=True)
        norway_res = await list_leads(page=1, page_size=20, country="Norway", db=db)
        print(f"    Filtered Norway count: {norway_res.total}", flush=True)
        assert norway_res.total >= 1
        assert norway_res.items[0].country == "Norway"

        print("[5] Testing Analytics Dashboard Aggregates...", flush=True)
        dash = await get_dashboard_metrics(db=db)
        print(f"    Total Discovered: {dash['summary']['total_leads_discovered']}", flush=True)
        print(f"    Verified Rate: {dash['summary']['verification_rate_pct']}%", flush=True)
        print(f"    High Priority (80-100): {dash['qualification_tiers']['high_priority_80_100']}", flush=True)
        print(f"    Potential (60-79): {dash['qualification_tiers']['potential_candidates_60_79']}", flush=True)
        print(f"    Low Priority (<60): {dash['qualification_tiers']['low_priority_below_60']}", flush=True)
        print(f"    Top Countries: {dash['top_countries']}", flush=True)

        print("\n[ALL CORE BACKEND ENGINE CHECKS VERIFIED SUCCESSFULLY!]", flush=True)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_all())
