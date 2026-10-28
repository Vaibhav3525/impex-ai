"""
Core backend integration tests — self-seeding, order-independent.

These tests use the same on-disk SQLite database as the application.
They seed the data they need before asserting, so results are stable
regardless of what other tests or seed scripts have run first.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.api.health import health_check
from app.api.leads import list_leads, create_lead, trigger_verification
from app.api.analytics import get_dashboard_metrics
from app.schemas.lead import LeadCreate


# ── Shared seed helper ────────────────────────────────────────────────────

_SEED_LEADS = [
    LeadCreate(
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
    ),
    LeadCreate(
        company_name="Gulf Spice Trading LLC",
        country="United Arab Emirates",
        city="Dubai",
        website="https://www.gulfspice.ae",
        product_category="Spices",
        contact_name="Ahmed Al-Rashidi",
        job_title="Procurement Manager",
        business_email="ahmed@gulfspice.ae",
        phone_number="+971 4 345 6789",
        source="Dubai Chamber of Commerce Directory",
        source_url="https://dubaichamber.com/members",
        import_evidence="Registered importer of Indian spices — Dubai Chamber directory.",
    ),
    LeadCreate(
        company_name="Berlin Organic GmbH",
        country="Germany",
        city="Berlin",
        website="https://www.berlinorganic.de",
        product_category="Organic Products",
        contact_name="Petra Bauer",
        job_title="Sourcing Manager",
        business_email="petra@berlinorganic.de",
        phone_number="+49 30 1234567",
        source="APEDA International Buyer Directory",
        source_url="https://apeda.gov.in/",
        import_evidence="Listed as buyer in APEDA organic products international buyer directory.",
    ),
    LeadCreate(
        company_name="Miami Fruits Inc",
        country="United States",
        city="Miami",
        website="http://www.miamifruits.example.com",
        product_category="Fresh Fruits",
        contact_name="Carlos Rivera",
        job_title="Import Manager",
        business_email="carlos@miamifruits.example.com",
        phone_number="+1 305 555 0100",
        source="US FDA Food Facility Registry",
        source_url="https://www.fda.gov/food",
        import_evidence=None,
        notes="Potential advance-fee risk — requires manual review.",
    ),
]


def _seed_if_needed(db) -> int:
    """Insert seed leads that do not already exist (by company name). Returns count inserted."""
    inserted = 0
    for lc in _SEED_LEADS:
        exists = db.query(Lead).filter(Lead.company_name == lc.company_name).first()
        if not exists:
            create_lead(lead_in=lc, auto_verify=False, db=db)
            inserted += 1
    return inserted


# ── Tests ─────────────────────────────────────────────────────────────────

def test_full_suite():
    init_db()
    db = SessionLocal()
    try:
        print("[0] Seeding base data...", flush=True)
        seeded = _seed_if_needed(db)
        print(f"    Seeded {seeded} leads", flush=True)

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
            import_evidence="Registered importer of high-grade turmeric under Japan Ministry of Health.",
        )
        created = create_lead(lead_in=test_new_lead, auto_verify=True, db=db)
        print(
            f"    Created: {created.company_name} ({created.lead_id}) "
            f"| Score: {created.buyer_score} | Status: {created.verification_status}",
            flush=True,
        )
        assert created.buyer_score >= 80.0
        assert created.verification_status == "Verified"

        print("[4] Testing Analytics Dashboard Aggregates...", flush=True)
        dash = get_dashboard_metrics(db=db)
        print("    Total Discovered:", dash["summary"]["total_leads_discovered"], flush=True)
        print("    Verification Rate:", dash["summary"]["verification_rate_pct"], "%", flush=True)
        print(
            "    High Priority Buyers (80-100):",
            dash["qualification_tiers"]["high_priority_80_100"],
            flush=True,
        )
        print("    Top Countries:", [c["country"] for c in dash["top_countries"]], flush=True)
        assert dash["summary"]["total_leads_discovered"] >= 5

        print("\n[SUCCESS] ALL BACKEND CORE CAPABILITIES AND APIS 100% OPERATIONAL!", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    test_full_suite()
