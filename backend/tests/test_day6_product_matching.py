"""
Day 6 Tests — Exporter Product Profiles & Buyer Qualification Matching Engine
Tests:
  - ProductProfile Model and CRUD operations
  - Semantic product relevance scoring
  - Excluded country hard disqualification (score = 0, tier = Disqualified)
  - Target country priority alignment
  - Import evidence and contact quality factors
  - Comprehensive explanation generation (PRD §5 invariant)
  - Batch lead matching & ranking for product profiles
  - Synchronous API endpoint invocation
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.models.product_profile import ProductProfile
from app.schemas.product_profile import (
    ProductProfileCreate,
    ProductProfileUpdate,
    ProductProfileResponse,
)
from app.schemas.lead import LeadCreate
from app.services.lead_service import ingest_lead
from app.services.qualification_service import (
    calculate_qualification_score,
    match_all_leads_for_product,
    evaluate_product_relevance,
    evaluate_country_alignment,
)
from app.api.products import (
    create_product_profile,
    list_product_profiles,
    get_product_profile,
    update_product_profile,
    delete_product_profile,
    match_leads_for_product_profile,
    qualify_single_lead_against_product,
)


@pytest.fixture(scope="module")
def db_session():
    """Module-level database session with initialized tables."""
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _create_sample_product(db: Session, suffix: str = "d6") -> ProductProfile:
    """Helper to create a standard exporter product profile."""
    prod = ProductProfile(
        product_name=f"Organic Basmati Rice {suffix}",
        product_category="Agricultural Commodities & Grains",
        hs_code="10063020",
        specifications="Average grain length 8.35mm, moisture 12.5% max, 100% sortex clean",
        grade="Grade A Extra Long",
        origin_country="India",
        available_quantity="1000 MT / Month",
        packaging="25kg & 50kg PP Woven Bags",
        moq="1x20ft FCL (20 MT)",
        target_price_min=1100.0,
        target_price_max=1350.0,
        currency="USD",
        incoterms="FOB Mundra Port",
        preferred_payment_terms="30% Advance + 70% against BL / Irrevocable LC at Sight",
        target_countries=["Saudi Arabia", "United Arab Emirates", "Germany", "United Kingdom"],
        excluded_countries=["SanctionedLand", "BannedRegion"],
        certifications=["APEDA", "FSSAI", "ISO 22000", "HACCP"],
        export_readiness=True,
        is_active=True,
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


def _create_sample_lead(db: Session, **kwargs) -> Lead:
    """Helper to create a custom lead for testing with unique deduplication identity."""
    import uuid
    uid = uuid.uuid4().hex[:6]
    defaults = {
        "company_name": f"Al-Noor Grain Imports {uid}",
        "country": "Saudi Arabia",
        "city": "Jeddah",
        "website": f"https://alnoorgrains-{uid}.sa",
        "product_category": "Basmati Rice & Grains",
        "contact_name": "Tariq Al-Mansoor",
        "job_title": "Head of Procurement",
        "business_email": f"tariq@{uid}-grains.sa",
        "phone_number": "+966 12 654 3210",
        "source": "APEDA International Buyer Directory",
        "source_url": "https://apeda.gov.in/",
        "import_evidence": "Consistently imports 10-15 FCL of Indian Basmati rice per quarter through Jeddah Islamic Port.",
        "notes": "Interested in 1121 and Traditional Basmati Rice FOB terms.",
    }
    defaults.update(kwargs)
    lead_in = LeadCreate(**defaults)
    lead, _ = ingest_lead(db, lead_in)
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# 1. Product Profile Model & Service Basics
# ─────────────────────────────────────────────────────────────────────────────

def test_create_and_query_product_profile(db_session):
    prod = _create_sample_product(db_session, suffix="test1")
    assert prod.id is not None
    assert prod.profile_id.startswith("prod_")
    assert prod.product_name.startswith("Organic Basmati Rice")
    assert "Saudi Arabia" in prod.target_countries
    assert prod.is_active is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. Excluded Country Hard Disqualification
# ─────────────────────────────────────────────────────────────────────────────

def test_hard_disqualification_for_excluded_country(db_session):
    prod = _create_sample_product(db_session, suffix="disq")
    
    # Lead from an explicitly excluded nation
    banned_lead = _create_sample_lead(
        db_session,
        company_name="Northern Trading House",
        country="SanctionedLand",
        business_email="ops@northerntrading.org",
    )
    
    result = calculate_qualification_score(banned_lead, prod)
    assert result.is_disqualified is True
    assert result.qualification_score == 0.0
    assert result.qualification_tier == "Disqualified"
    assert "SanctionedLand" in (result.disqualification_reason or "")
    assert "excluded trade regions" in result.explanation.lower()
    assert "do not initiate outreach" in result.recommended_action.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Country Alignment Scoring
# ─────────────────────────────────────────────────────────────────────────────

def test_country_alignment_target_market(db_session):
    prod = _create_sample_product(db_session, suffix="tgt")
    lead_target = _create_sample_lead(db_session, country="Saudi Arabia")
    
    score, disq, reason, explanation = evaluate_country_alignment(lead_target, prod)
    assert score == 25.0
    assert disq is False
    assert "high-priority" in explanation.lower()


def test_country_alignment_open_market(db_session):
    prod = _create_sample_product(db_session, suffix="open")
    # Norway is not in target_countries ["Saudi Arabia", "UAE", "Germany", "UK"]
    # and not in excluded_countries ["SanctionedLand", "BannedRegion"]
    lead_open = _create_sample_lead(db_session, country="Norway", company_name="Fjord Foods AS")
    
    score, disq, reason, explanation = evaluate_country_alignment(lead_open, prod)
    assert score == 12.0
    assert disq is False
    assert "open non-priority" in explanation.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Product Relevance & Semantic Overlap
# ─────────────────────────────────────────────────────────────────────────────

def test_product_relevance_direct_match(db_session):
    prod = _create_sample_product(db_session, suffix="rel1")
    lead = _create_sample_lead(
        db_session,
        product_category=prod.product_name, # Exact product category match
    )
    
    score, evidence = evaluate_product_relevance(lead, prod)
    assert score == 30.0
    assert any("Direct product category match" in e for e in evidence)


def test_product_relevance_keyword_overlap(db_session):
    prod = _create_sample_product(db_session, suffix="rel2")
    lead = _create_sample_lead(
        db_session,
        company_name="Arabian Rice Milling",
        product_category="Premium Long Grain White Rice",
        import_evidence="Annual tenders for imported Basmati and non-basmati rice.",
    )
    
    score, evidence = evaluate_product_relevance(lead, prod)
    assert score >= 20.0
    assert any("commodity overlap" in e.lower() for e in evidence)


def test_product_relevance_unrelated_commodity(db_session):
    prod = _create_sample_product(db_session, suffix="rel3")
    lead = _create_sample_lead(
        db_session,
        company_name="Steel & Tube Logistics",
        product_category="Industrial Seamless Pipes & Fittings",
        import_evidence="Importer of hot-rolled carbon steel tubing.",
        notes="No food products handled.",
    )
    
    score, evidence = evaluate_product_relevance(lead, prod)
    assert score == 0.0
    assert any("No direct product keyword overlap" in e for e in evidence)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Composite Qualification Invariant & Detailed Explanation Check
# ─────────────────────────────────────────────────────────────────────────────

def test_high_priority_buyer_qualification(db_session):
    prod = _create_sample_product(db_session, suffix="high")
    lead = _create_sample_lead(
        db_session,
        company_name="Gulf Royal Cereals Est",
        country="Saudi Arabia",
        city="Riyadh",
        product_category="Organic Basmati Rice",
        contact_name="Fahad Al-Husseini",
        job_title="Procurement Director",
        business_email="fahad@gulfroyalcereals.com",
        phone_number="+966 11 400 1234",
        import_evidence="Regular commercial buyer of Indian 1121 Organic Basmati Rice with active import license.",
    )
    # Set verification score high
    lead.buyer_score = 88.0
    lead.verification_status = "Verified"
    db_session.commit()

    result = calculate_qualification_score(lead, prod)
    
    # Assertions
    assert result.qualification_score >= 80.0
    assert result.qualification_tier == "Highly Qualified"
    assert result.is_disqualified is False
    assert result.breakdown.product_relevance_score > 0
    assert result.breakdown.country_alignment_score == 25.0
    assert result.breakdown.import_evidence_score == 20.0
    assert result.breakdown.contact_quality_score > 0
    assert result.breakdown.verification_readiness_score == 10.0
    
    # PRD §5 Invariant: Explanation must explain WHY the buyer qualified
    assert "Qualification Assessment:" in result.explanation
    assert "Product Match" in result.explanation
    assert "Destination Market" in result.explanation
    assert "Import Credibility" in result.explanation
    assert "Verification Standing" in result.explanation
    assert "Mode A" in result.recommended_action


# ─────────────────────────────────────────────────────────────────────────────
# 6. match_all_leads_for_product Batch Filtering
# ─────────────────────────────────────────────────────────────────────────────

def test_match_all_leads_ordering(db_session):
    prod = _create_sample_product(db_session, suffix="batch")
    
    # Create one highly relevant lead
    lead_good = _create_sample_lead(
        db_session,
        company_name="Hamburg Rice Import GmbH",
        country="Germany",
        product_category="Organic Basmati Rice",
        business_email="import@hamburgrice.de",
    )
    
    # Create one completely irrelevant lead
    lead_bad = _create_sample_lead(
        db_session,
        company_name="AutoParts Central",
        country="Germany",
        product_category="Automotive Transmission Gears",
        business_email="purchasing@autoparts.de",
        import_evidence=None,
    )
    
    matches = match_all_leads_for_product(db_session, prod, min_score=0.0, limit=5000)
    assert len(matches) >= 2
    
    # Verify descending sort order
    scores = [m.qualification_score for m in matches]
    assert scores == sorted(scores, reverse=True)
    
    # Good lead should rank before bad lead
    good_match = next((m for m in matches if m.company_name == "Hamburg Rice Import GmbH"), None)
    bad_match = next((m for m in matches if m.company_name == "AutoParts Central"), None)
    assert good_match is not None
    assert bad_match is not None
    assert good_match.qualification_score > bad_match.qualification_score


# ─────────────────────────────────────────────────────────────────────────────
# 7. Synchronous API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

def test_api_create_and_list_products(db_session):
    req = ProductProfileCreate(
        product_name="Kashmiri Saffron Grade 1",
        product_category="Spices & Seasonings",
        hs_code="09102010",
        specifications="Mongra Saffron, ISO 3632 Category 1, Crocin > 220",
        origin_country="India",
        target_countries=["United States", "France", "Spain"],
        excluded_countries=["ConflictZone"],
        currency="USD",
        incoterms="CIF Air Cargo",
        preferred_payment_terms="100% Advance or Irrevocable LC at Sight",
    )
    created = create_product_profile(product_in=req, db=db_session)
    assert created.id is not None
    assert created.product_name == "Kashmiri Saffron Grade 1"

    # List products
    all_prods = list_product_profiles(active_only=True, db=db_session)
    assert len(all_prods) >= 1
    assert any(p.product_name == "Kashmiri Saffron Grade 1" for p in all_prods)


def test_api_update_product(db_session):
    prod = _create_sample_product(db_session, suffix="upd")
    
    updates = ProductProfileUpdate(
        target_price_min=1250.0,
        moq="2x20ft FCL (40 MT)",
    )
    updated = update_product_profile(product_id=prod.profile_id, updates=updates, db=db_session)
    assert updated.target_price_min == 1250.0
    assert updated.moq == "2x20ft FCL (40 MT)"


def test_api_match_leads_for_product(db_session):
    prod = _create_sample_product(db_session, suffix="match_api")
    summary = match_leads_for_product_profile(
        product_id=prod.profile_id,
        min_score=0.0,
        include_disqualified=True,
        limit=20,
        db=db_session,
    )
    assert summary.total_leads_evaluated >= 1
    assert summary.product_profile.profile_id == prod.profile_id
    assert isinstance(summary.top_matches, list)


def test_api_qualify_single_lead(db_session):
    prod = _create_sample_product(db_session, suffix="single_api")
    lead = _create_sample_lead(db_session, company_name="Single Qualify Test Corp")
    
    result = qualify_single_lead_against_product(
        lead_id=lead.lead_id,
        product_id=prod.profile_id,
        db=db_session,
    )
    assert result.lead_id == lead.lead_id
    assert result.product_name == prod.product_name
    assert result.qualification_score >= 0.0
    assert len(result.explanation) > 20
