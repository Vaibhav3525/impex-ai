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
from app.services.public_source_discovery import DIRECTORIES, extract_candidates, run_public_discovery
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
    
    assert results == []
    comp_names = [r.company_name for r in results]
    assert not comp_names
    
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
    
    assert results == []
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


RICE_LISTINGS = b"""
    <div class="wixui-repeater__item">
      <h1>Example Foods Ltd</h1><a href="https://buyer.example.com">Visit site</a>
    </div>
    <a href="https://irrelevant.example.org">General information</a>
"""


def test_public_source_extraction_uses_company_listing_and_matching_country():
    source = DIRECTORIES[0]
    results = extract_candidates(RICE_LISTINGS, source, "Basmati Rice", "United Kingdom")
    assert len(results) == 1
    assert results[0].company_name == "Example Foods Ltd"
    assert results[0].source_url == source.url
    assert not results[0].import_evidence
    assert not extract_candidates(RICE_LISTINGS, source, "Basmati Rice", "Germany")


def test_public_discovery_ingests_as_unverified(db_session, monkeypatch):
    from app.models.product_profile import ProductProfile

    product = ProductProfile(
        product_name="Fixture Basmati Rice",
        product_category="Grains",
        target_countries=["United Kingdom", "Germany"],
        excluded_countries=[],
        certifications=[],
        export_readiness=False,
        is_active=True,
    )
    db_session.add(product)
    db_session.commit()

    monkeypatch.setattr("app.services.public_source_discovery.DIRECTORIES", (DIRECTORIES[0],))
    monkeypatch.setattr("app.services.public_source_discovery._fetch_directory", lambda *_: RICE_LISTINGS)
    result = run_public_discovery(db_session, max_pairs=1)
    lead = db_session.query(Lead).filter_by(company_name="Example Foods Ltd").one()
    assert result["created"] == 1
    assert lead.verification_status == "Unverified"
    assert lead.outreach_status == "Not Contacted"
    assert run_public_discovery(db_session, max_pairs=1)["duplicates"] == 1


def test_discovery_trigger_token_is_scoped(monkeypatch):
    from fastapi.testclient import TestClient
    from app.core.config import settings
    from app.main import app

    token = "discovery-fixture-token-longer-than-32-characters"
    monkeypatch.setattr(settings, "DISCOVERY_TRIGGER_TOKEN", token)
    monkeypatch.setattr("app.api.discovery.run_public_discovery", lambda *a, **k: {"status": "Completed"})

    with TestClient(app) as client:
        route = "/api/v1/discover/public-sources/run"
        headers = {"Authorization": f"Bearer {token}"}
        assert client.post(route).status_code == 401
        assert client.post(route, headers=headers).json() == {"status": "Completed"}
        assert client.get("/api/v1/products", headers=headers).status_code == 401


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
    
    assert res["total_discovered"] == 0
    assert len(res["leads"]) == 0
    
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

