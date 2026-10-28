"""
Autonomous Lead Discovery & Generation Engine Tests
PRD §3: Validates multi-channel international buyer discovery across
public trade directories, Indian Embassy commercial missions, web HTML scraping,
and compliant LinkedIn persona generation.
"""

import pytest
from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.services.lead_discovery_crawler import LeadDiscoveryCrawler
from app.services.embassy_directory_connector import EmbassyDirectoryConnector
from app.services.linkedin_dork_service import LinkedInDorkService
from app.api.discovery import (
    run_autonomous_lead_discovery,
    search_embassy_directories,
    generate_linkedin_xray_queries,
    AutonomousSearchRequest,
    EmbassySearchRequest,
    LinkedInDorkRequest
)


@pytest.fixture
def db_session():
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_crawler_search_and_discover_by_commodity():
    """Crawler accurately matches international buyers by commodity terms."""
    crawler = LeadDiscoveryCrawler()
    
    # Search for Basmati Rice buyers
    results = crawler.search_and_discover(commodity="Basmati Rice", country="All", limit=5)
    
    assert len(results) >= 2
    comp_names = [r.company_name for r in results]
    assert any("Al Maya" in c or "Lulu" in c or "Binzagr" in c or "Euryza" in c for c in comp_names)
    
    # Each lead must contain mandatory buyer fields
    for lead in results:
        assert lead.company_name
        assert lead.country
        assert lead.product_category
        assert lead.business_email
        assert lead.source_url
        assert lead.import_evidence


def test_crawler_filter_by_country():
    """Crawler strictly filters results by designated target market country."""
    crawler = LeadDiscoveryCrawler()
    
    results = crawler.search_and_discover(commodity="Spices", country="Germany", limit=10)
    
    assert len(results) > 0
    for lead in results:
        assert lead.country == "Germany"


def test_crawler_html_metadata_and_evidence_extraction():
    """Extracts schema.org JSON-LD, public business emails, and import evidence from HTML."""
    crawler = LeadDiscoveryCrawler()
    
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
      <title>Hamburg Grain & Rice Importers GmbH - Direct Ocean Freight Distribution</title>
      <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "WholesaleStore",
        "name": "Hamburg Grain & Rice Importers GmbH",
        "telephone": "+49 40 1234 5678",
        "email": "purchasing@hamburggrains.de"
      }
      </script>
    </head>
    <body>
      <h1>Global Commodity Sourcing</h1>
      <p>We are a direct importer and distributor of Indian basmati rice and organic pulses.</p>
      <p>We receive regular ocean freight container shipments through Port of Hamburg.</p>
      <div>Contact our sourcing team: import@hamburggrains.de or call +49 40 9876 5432</div>
    </body>
    </html>
    """
    
    extracted = crawler.extract_company_from_html(sample_html, "https://www.hamburggrains.de")
    
    assert extracted["company_name"] == "Hamburg Grain & Rice Importers GmbH"
    assert extracted["schema_extracted"] is True
    assert extracted["business_email"] in ["purchasing@hamburggrains.de", "import@hamburggrains.de"]
    assert extracted["import_evidence"] is not None
    assert "direct importer" in extracted["import_evidence"].lower()


def test_embassy_directory_connector_retrieves_missions():
    """Embassy connector retrieves vetted buyers from Indian Commercial Missions."""
    connector = EmbassyDirectoryConnector()
    
    # 1. Fetch UK mission buyers
    uk_leads = connector.fetch_embassy_leads(country="United Kingdom")
    assert len(uk_leads) >= 2
    assert any("Natco" in l.company_name or "East End" in l.company_name for l in uk_leads)
    assert any("High Commission of India, London" in l.source for l in uk_leads)

    # 2. Fetch UAE mission buyers
    uae_leads = connector.fetch_embassy_leads(country="United Arab Emirates")
    assert len(uae_leads) >= 2
    assert any("Jaleel" in l.company_name or "Choithram" in l.company_name for l in uae_leads)


def test_linkedin_dork_service_generates_compliant_queries():
    """LinkedIn dork engine generates valid, non-scraping Google X-Ray search strings."""
    service = LinkedInDorkService()
    
    res = service.generate_xray_queries(commodity="Basmati Rice", country="United Arab Emirates")
    
    assert "site:linkedin.com/in/" in res["individual_xray_query"]
    assert '"Basmati Rice"' in res["individual_xray_query"]
    assert '"United Arab Emirates"' in res["individual_xray_query"]
    assert "site:linkedin.com/company/" in res["company_xray_query"]
    assert "https://www.google.com/search?q=" in res["individual_search_url"]
    assert "100% PRD §3.D Compliant" in res["compliance_status"]


def test_autonomous_lead_discovery_api_flow(db_session):
    """End-to-end API test: runs discovery, ingests leads, deduplicates, and auto-verifies."""
    req = AutonomousSearchRequest(
        commodity="Black Pepper & Cardamom",
        country="Germany",
        sources=["directories", "embassy"],
        limit=5,
        auto_ingest=True,
        auto_verify=True
    )
    
    res = run_autonomous_lead_discovery(req, db=db_session)
    
    assert res["total_discovered"] > 0
    assert len(res["leads"]) > 0
    
    # Verify records persisted in database
    for l_dict in res["leads"]:
        db_lead = db_session.query(Lead).filter(Lead.company_name == l_dict["company_name"]).first()
        assert db_lead is not None
        assert db_lead.verification_status in ["Verified", "Partially Verified", "Unverified"]
        assert db_lead.buyer_score >= 0.0

    # Test deduplication: running identical discovery again should report duplicates
    res_repeat = run_autonomous_lead_discovery(req, db=db_session)
    assert res_repeat["duplicate_leads_updated"] >= res["created_new_leads"]


def test_embassy_and_linkedin_api_endpoints(db_session):
    """Test embassy and LinkedIn API routes."""
    # 1. Embassy API
    emb_req = EmbassySearchRequest(country="Saudi Arabia", commodity="Rice", auto_ingest=False)
    emb_res = search_embassy_directories(emb_req, db=db_session)
    assert emb_res["total_leads_found"] > 0
    assert any("Al Babtain" in l.company_name or "Al Munajem" in l.company_name for l in emb_res["leads"])

    # 2. LinkedIn Dork API
    li_req = LinkedInDorkRequest(commodity="Organic Spices", country="United Kingdom")
    li_res = generate_linkedin_xray_queries(li_req)
    assert "individual_xray_query" in li_res
    assert "Procurement" in li_res["individual_xray_query"]
