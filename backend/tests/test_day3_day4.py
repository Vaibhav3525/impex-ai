"""
Day 3 & 4 Integration Tests:
- Batch ingestion validation logic
- CSV/JSON parsing
- Field normalization & alias resolution
- Duplicate detection in batch import
- APEDA, ITP, and UN Comtrade connector logic
- Batch Import API endpoints
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.services.batch_ingestion import (
    parse_csv_bytes, parse_json_bytes, validate_row,
    normalize_header, BatchImportResult, RowResult
)
from app.services.trade_connectors import (
    APEDADirectoryConnector, IndianTradePortalConnector
)
from app.api.import_leads import _run_batch
from app.api.discovery import _ingest_discovered

# In-memory test DB
TEST_DB_URL = "sqlite:///:memory:"
engine_t = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine_t)


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.create_all(bind=engine_t)
    yield
    Base.metadata.drop_all(bind=engine_t)


# ─────────────────────────────────────────────
# Batch Ingestion Unit Tests
# ─────────────────────────────────────────────

def test_normalize_header_aliases():
    assert normalize_header("Company") == "company_name"
    assert normalize_header("Email Address") == "business_email"
    assert normalize_header("Telephone") == "phone_number"
    assert normalize_header("Commodity") == "product_category"
    assert normalize_header("URL") == "website"


def test_validate_row_valid():
    row = {
        "company_name": "Nordic Imports AS",
        "country": "Norway",
        "product_category": "Basmati Rice",
        "source": "APEDA Directory",
        "business_email": "info@nordicimports.example.no",
        "website": "nordicimports.example.no",
    }
    cleaned, errors, warnings = validate_row(row, 1)
    assert errors == []
    assert cleaned["company_name"] == "Nordic Imports AS"
    # Website should be auto-prefixed
    assert cleaned["website"].startswith("https://")
    assert any("https" in w for w in warnings)


def test_validate_row_missing_required_fields():
    row = {"company_name": "Acme", "country": "Japan"}  # Missing product_category & source
    cleaned, errors, warnings = validate_row(row, 1)
    error_fields = " ".join(errors)
    assert "product_category" in error_fields
    assert "source" in error_fields


def test_validate_row_free_email_warning():
    row = {
        "company_name": "Quick Deals LLC",
        "country": "USA",
        "product_category": "Rice",
        "source": "Web Forum",
        "business_email": "quickbuyer@gmail.com",
    }
    cleaned, errors, warnings = validate_row(row, 1)
    assert errors == []  # not a hard error, just a warning
    assert any("gmail" in w.lower() for w in warnings)


def test_validate_row_strips_external_score():
    row = {
        "company_name": "Score Injector Ltd",
        "country": "UK",
        "product_category": "Spices",
        "source": "Test",
        "buyer_score": "99",
    }
    cleaned, errors, warnings = validate_row(row, 1)
    assert "buyer_score" not in cleaned
    assert any("score" in w.lower() for w in warnings)


def test_parse_csv_bytes_basic():
    csv_content = (
        "company_name,country,product_category,source\n"
        "Test Corp,Germany,Spices,Trade Fair\n"
        "Beta Imports,Japan,Rice,ITP\n"
    ).encode("utf-8")
    rows = parse_csv_bytes(csv_content)
    assert len(rows) == 2
    assert rows[0]["company_name"] == "Test Corp"
    assert rows[1]["country"] == "Japan"


def test_parse_json_bytes_list():
    data = [
        {"company_name": "Alpha Imports", "country": "France", "product_category": "Wheat", "source": "ITP"},
        {"company_name": "Beta Foods", "country": "Germany", "product_category": "Spices", "source": "APEDA"},
    ]
    rows = parse_json_bytes(json.dumps(data).encode("utf-8"))
    assert len(rows) == 2
    assert rows[0]["company_name"] == "Alpha Imports"


def test_parse_json_bytes_envelope():
    data = {"leads": [
        {"company_name": "Gamma Ltd", "country": "UK", "product_category": "Rice", "source": "Test"},
    ]}
    rows = parse_json_bytes(json.dumps(data).encode("utf-8"))
    assert len(rows) == 1
    assert rows[0]["company_name"] == "Gamma Ltd"


def test_batch_import_deduplication():
    db = TestSession()
    try:
        rows = [
            {"company_name": "Omega Grains BV", "country": "Netherlands",
             "product_category": "Basmati Rice", "source": "APEDA",
             "business_email": "info@omegagrains.example.nl"},
            # Exact duplicate
            {"company_name": "Omega Grains BV", "country": "Netherlands",
             "product_category": "Basmati Rice", "source": "Duplicate Row",
             "business_email": "info@omegagrains.example.nl"},
        ]
        result = _run_batch(rows, "test_dedup.csv", auto_verify=False, db=db)
        assert result.created == 1
        assert result.duplicates == 1
        assert result.errors == 0
    finally:
        db.close()


def test_batch_import_error_on_missing_required():
    db = TestSession()
    try:
        rows = [
            {"company_name": "Valid Co", "country": "France",
             "product_category": "Spices", "source": "Test"},
            {"company_name": "", "country": "Germany",
             "product_category": "Rice"},  # Missing source & company_name
        ]
        result = _run_batch(rows, "test_errors.csv", auto_verify=False, db=db)
        assert result.created == 1
        assert result.errors == 1
    finally:
        db.close()


def test_batch_with_auto_verify():
    db = TestSession()
    try:
        rows = [
            {
                "company_name": "Zurich Spices Trading AG",
                "country": "Switzerland",
                "city": "Zurich",
                "product_category": "Organic Spices",
                "source": "Swiss Trade Directory",
                "source_url": "https://swiss-trade.example.ch",
                "business_email": "trade@zurichspices.example.ch",
                "website": "https://zurichspices.example.ch",
                "contact_name": "Hans Müller",
                "job_title": "Head of Procurement",
                "import_evidence": "Registered organic importer under Swiss FSVO regulations.",
            }
        ]
        result = _run_batch(rows, "verified_import.csv", auto_verify=True, db=db)
        assert result.created == 1
        assert result.errors == 0
        assert result.rows[0].lead_id is not None
    finally:
        db.close()


# ─────────────────────────────────────────────
# Trade Connector Unit Tests
# ─────────────────────────────────────────────

def test_apeda_connector_valid_row():
    connector = APEDADirectoryConnector()
    row = {
        "importer_name": "Tokyo Rice Importers KK",
        "country": "Japan",
        "product": "Basmati Rice",
        "email": "trade@tokyorice.example.jp",
        "website": "tokyorice.example.jp",
        "contact_person": "Kenji Tanaka",
        "designation": "Purchasing Manager",
    }
    lead = connector.process_directory_row(row)
    assert lead is not None
    assert lead.company_name == "Tokyo Rice Importers KK"
    assert lead.country == "Japan"
    assert lead.source == "APEDA International Buyer Directory"
    assert lead.website.startswith("https://")
    assert "APEDA" in lead.import_evidence


def test_apeda_connector_invalid_row_skipped():
    connector = APEDADirectoryConnector()
    # Missing product
    row = {"importer_name": "Acme", "country": "USA"}
    lead = connector.process_directory_row(row)
    assert lead is None


def test_apeda_batch_processing():
    connector = APEDADirectoryConnector()
    rows = [
        {"importer_name": "Nordic Organic AS", "country": "Norway",
         "product": "Organic Spices", "email": "buy@nordicorganic.example.no"},
        {"importer_name": "", "country": "Germany", "product": "Rice"},  # invalid
        {"importer_name": "Paris Imports SA", "country": "France",
         "product": "Basmati Rice", "email": "info@paris-imports.example.fr"},
    ]
    leads = connector.process_directory_rows(rows)
    assert len(leads) == 2
    assert leads[0].company_name == "Nordic Organic AS"
    assert leads[1].company_name == "Paris Imports SA"


def test_itp_connector_valid_lead():
    connector = IndianTradePortalConnector()
    lead_data = {
        "buyer_name": "Gulf Food Traders LLC",
        "buyer_country": "UAE",
        "buyer_city": "Dubai",
        "product_description": "Non-Basmati Rice",
        "buyer_email": "procurement@gulffood.example.ae",
        "contact_person": "Ahmed Al-Rashid",
        "quantity_required": "500 MT per month",
    }
    lead = connector.process_trade_lead(lead_data)
    assert lead is not None
    assert lead.company_name == "Gulf Food Traders LLC"
    assert lead.country == "UAE"
    assert lead.source == "Indian Trade Portal"
    assert "500 MT" in (lead.notes or "")


def test_itp_connector_skips_missing_company():
    connector = IndianTradePortalConnector()
    lead_data = {"buyer_country": "UK", "product_description": "Spices"}
    lead = connector.process_trade_lead(lead_data)
    assert lead is None


def test_ingest_discovered_dedup():
    from app.services.trade_connectors import DiscoveredLead
    db = TestSession()
    try:
        dl1 = DiscoveredLead(
            company_name="Singapore Spice Importers Pte Ltd",
            country="Singapore",
            product_category="Cardamom",
            source="Singapore Trade Board",
            source_url="https://stb.example.sg",
        )
        # Same company, second time
        dl2 = DiscoveredLead(
            company_name="Singapore Spice Importers Pte Ltd",
            country="Singapore",
            product_category="Cardamom",
            source="Singapore Trade Board",
            source_url="https://stb.example.sg",
        )
        result1 = _ingest_discovered([dl1], auto_verify=False, db=db)
        result2 = _ingest_discovered([dl2], auto_verify=False, db=db)
        assert result1["created"] == 1
        assert result2["duplicates"] == 1
        assert result2["created"] == 0
    finally:
        db.close()
