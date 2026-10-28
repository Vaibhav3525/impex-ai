"""
Unit tests for Lead Ingestion, Deduplication, and the 100-Point Verification Engine.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.lead import Lead
from app.schemas.lead import LeadCreate
from app.services.lead_service import ingest_lead, normalize_company_name, extract_domain
from app.services.verification_service import run_lead_verification, evaluate_email_quality

# Use in-memory SQLite for rapid isolation testing
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_company_normalization():
    assert normalize_company_name("Acme Imports Ltd.") == "acme imports"
    assert normalize_company_name("Global Foods Corp, LLC") == "global foods"
    assert normalize_company_name("Nordic Spices GmbH") == "nordic spices"

def test_extract_domain():
    assert extract_domain("https://www.example.com/contact") == "example.com"
    assert extract_domain("john@acme.de") == "acme.de"
    assert extract_domain("http://sub.domain.co.uk/path") == "sub.domain.co.uk"

def test_email_quality_evaluation():
    score, flags = evaluate_email_quality("buyer@company.com")
    assert score == 15.0
    assert len(flags) == 0

    score_free, flags_free = evaluate_email_quality("quickdeals@gmail.com")
    assert score_free == 2.0
    assert "FLAG_FREE_EMAIL_DOMAIN" in flags_free

def test_lead_ingestion_and_deduplication():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        lead_data_1 = LeadCreate(
            company_name="Apex Global Trading Ltd",
            country="United Kingdom",
            city="London",
            website="https://apexglobal.example.co.uk",
            product_category="Basmati Rice",
            contact_name="James Wilson",
            job_title="Procurement Director",
            business_email="j.wilson@apexglobal.example.co.uk",
            source="Official UK Importers Registry"
        )
        lead_1, created_1 = ingest_lead(db, lead_data_1)
        assert created_1 is True
        assert lead_1.lead_id.startswith("LID-")

        # Ingest exact duplicate with slight punctuation variance
        lead_data_2 = LeadCreate(
            company_name="Apex Global Trading Limited",
            country="United Kingdom",
            website="https://www.apexglobal.example.co.uk/",
            product_category="Basmati Rice",
            source="Directory B"
        )
        lead_2, created_2 = ingest_lead(db, lead_data_2)
        assert created_2 is False
        assert lead_2.lead_id == lead_1.lead_id

        # Verify scoring
        log = run_lead_verification(db, lead_1)
        assert lead_1.buyer_score >= 60.0
        assert lead_1.verification_status in ["Verified", "Partially Verified"]
        assert log.total_score == lead_1.buyer_score
    finally:
        db.close()

