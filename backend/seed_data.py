"""
Seed script to populate initial validated international buyer records,
demonstrating the 100-point verification engine and duplicate detection.
"""
from app.core.database import SessionLocal, Base, engine
from app.schemas.lead import LeadCreate
from app.services.lead_service import ingest_lead
from app.services.verification_service import run_lead_verification

# Ensure tables exist
Base.metadata.create_all(bind=engine)

SAMPLE_BUYERS = [
    LeadCreate(
        company_name="Nordic Grains & Spices AS",
        country="Norway",
        city="Oslo",
        website="https://www.nordicgrains.example.no",
        product_category="Basmati Rice & Organic Spices",
        contact_name="Erik Solberg",
        job_title="Head of Procurement",
        business_email="erik.solberg@nordicgrains.example.no",
        phone_number="+47 22 88 44 00",
        source="APEDA International Buyer Directory",
        source_url="https://apeda.gov.in/buyer-directory/norway-importers.pdf",
        import_evidence="Registered grain and organic spice importer under Norwegian Food Safety Authority (Mattilsynet).",
        notes="Consistently imports 50+ FCL containers of long-grain rice annually."
    ),
    LeadCreate(
        company_name="Gulf Agro Commodities FZE",
        country="United Arab Emirates",
        city="Dubai",
        website="https://www.gulfagro.example.ae",
        product_category="Non-Basmati Rice & Pulses",
        contact_name="Tariq Al-Mansoor",
        job_title="Managing Director",
        business_email="tariq@gulfagro.example.ae",
        phone_number="+971 4 332 9911",
        source="Indian Trade Portal Trade Leads",
        source_url="https://www.indiantradeportal.in/trade-leads/uae-rice",
        import_evidence="Active Dubai Multi Commodities Centre (DMCC) trade license holder with Jebel Ali port clearance history.",
        notes="Interested in 1000 MT parboiled non-basmati rice under Irrevocable LC."
    ),
    LeadCreate(
        company_name="Bavaria Gourmet Foods GmbH",
        country="Germany",
        city="Munich",
        website="https://www.bavaria-gourmet.example.de",
        product_category="Cardamom, Black Pepper & Turmeric",
        contact_name="Klaus Weber",
        job_title="Senior Sourcing Manager",
        business_email="klaus.weber@bavaria-gourmet.example.de",
        phone_number="+49 89 55443322",
        source="Indo-German Chamber of Commerce Directory",
        source_url="https://indo-german.example.org/directory/food-importers",
        import_evidence="EU TRACES registered organic importer; regular attendee at BioFach Nuremberg trade fair.",
        notes="High quality specifications required: pesticide residues strictly adhering to EU MRL limits."
    ),
    LeadCreate(
        company_name="Suspicious Quick Trades LLC",
        country="United States",
        city="Miami",
        website="http://quicktrades-temp.biz",
        product_category="Any Export Commodity",
        contact_name="John Anonymous",
        job_title="Agent",
        business_email="quickbuyer2026@gmail.com",
        phone_number="+1 305 000 0000",
        source="Unverified Web Forum",
        source_url="http://trade-forum-leads.example.com",
        import_evidence=None,
        notes="Demands upfront supplier registration fee of $500 before sending purchase order."
    )
]

def run_seed():
    db = SessionLocal()
    print("🌱 Seeding realistic test international buyer leads...")
    try:
        for buyer_data in SAMPLE_BUYERS:
            lead, is_created = ingest_lead(db, buyer_data)
            status_str = "Created" if is_created else "Updated"
            print(f"[{status_str}] {lead.company_name} ({lead.country}) - ID: {lead.lead_id}")
            
            # Run verification engine
            log = run_lead_verification(db, lead)
            print(f"   -> Verification: {lead.verification_status} | Score: {lead.buyer_score}/100 | Flags: {lead.risk_flags}")
            print(f"   -> Risk Level: {log.risk_level}")
        print("\n✅ Seeding complete. All initial records verified and logged.")
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
