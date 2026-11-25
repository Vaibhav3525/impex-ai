import json
import uuid
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.models.lead import Lead
from app.models.deal import Deal
from app.models.outreach import OutreachEmail
from app.models.product_profile import ProductProfile
from app.models.evidence import ReviewedEvidence
from app.services.verification_service import run_lead_verification
from app.services.smtp_service import send_outreach_email
from app.services.payment_risk import assess_deal_financial_risk
from app.services.email_composer import compose_grounded_email
from app.schemas.proforma import InvoiceItem, ProformaInvoiceCreate

@pytest.fixture
def db():
    init_db()
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def buyer(db):
    uid = uuid.uuid4().hex
    lead = Lead(lead_id=uid, company_name="Fictional regression fixture", country="Germany", city="Hamburg", website="https://fixture.invalid", product_category="Rice", business_email="buyer@fixture.invalid", source="Unsubstantiated registry", source_url="https://example.org", import_evidence="Operator typed an import claim here", dedup_hash=uid, verification_status="Verified", risk_level="LOW")
    db.add(lead); db.commit()
    return lead

def test_populated_profile_cannot_verify_a_fictional_buyer(db, buyer):
    log = run_lead_verification(db, buyer, run_live_checks=False)
    assert log.total_score == 0
    assert buyer.verification_status == "Unverified"

def test_reviewed_documents_can_support_verification(db, buyer):
    buyer.source_url = "https://registry.company.de/record/123"
    for category in ["identity", "relevance", "website", "email", "imports", "independent"]:
        db.add(ReviewedEvidence(lead_id=buyer.lead_id, category=category, source_url=buyer.source_url, document_reference="Fixture document 123", finding="Reviewed explicit evidence for this test category.", reviewed_by="operator"))
    db.commit()
    run_lead_verification(db, buyer, run_live_checks=False)
    assert buyer.verification_status == "Verified"
    assert buyer.buyer_score == 100

def test_admin_api_requires_authentication():
    with TestClient(app) as client:
        assert client.get("/api/v1/leads").status_code == 401
        assert client.post("/api/v1/outreach/dispatch-batch").status_code == 401
        assert client.post("/api/v1/replies/incoming", json={}).status_code == 401

def test_cookie_login_and_csrf_protection():
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/login", json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD})
        assert res.status_code == 200
        assert "HttpOnly" in res.headers["set-cookie"]
        assert client.get("/api/v1/leads").status_code == 200
        assert client.post("/api/v1/outreach/dispatch-batch").status_code == 403
        assert client.post("/api/v1/auth/logout", headers={"origin": "http://testserver", "x-requested-with": "impex-ui"}).status_code == 200
        assert client.get("/api/v1/leads").status_code == 401

def test_no_credentials_never_reports_sent(db, buyer, monkeypatch):
    monkeypatch.setattr(settings, "OUTREACH_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_USER", "")
    email = OutreachEmail(lead_id=buyer.lead_id, to_email=buyer.business_email, company_name=buyer.company_name, country=buyer.country, subject="Fixture", body_text="Fixture", status="Approved", approved_by="operator")
    db.add(email); db.commit()
    result = send_outreach_email(db, email.email_id)
    assert result["success"] is False
    assert email.status == "Approved"
    assert email.sent_at is None

def test_approval_identity_is_not_supplied_by_caller(db, buyer):
    email = OutreachEmail(lead_id=buyer.lead_id, to_email=buyer.business_email, company_name=buyer.company_name, country=buyer.country, subject="Fixture", body_text="Fixture", status="Queued")
    db.add(email); db.commit()
    with TestClient(app) as client:
        res = client.post(f"/api/v1/outreach/emails/{email.email_id}/approve", headers={"Authorization": "Bearer " + settings.ADMIN_PASSWORD}, json={"reviewer_name": "Forged manager"})
        assert res.status_code == 200
        assert res.json()["approved_by"] == settings.ADMIN_USERNAME

@pytest.mark.parametrize("terms,expected", [("100% advance within 5 days", "Approved"), ("unconfirmed lc", "Under Review"), ("Open account 60 days", "Blocked"), ("CAD", "Approved"), ("D/A 90", "Blocked")])
def test_payment_terms_are_parsed_as_terms(buyer, terms, expected):
    deal = Deal(deal_id="test", lead_id=buyer.lead_id, product_name="Rice", payment_terms=terms)
    assert assess_deal_financial_risk(deal, buyer)["status"] == expected

def test_confirmation_requires_payment_proof(db, buyer):
    from app.api.pipeline import update_deal_stage
    from app.schemas.deal import StageTransitionRequest
    deal = Deal(deal_id=uuid.uuid4().hex, lead_id=buyer.lead_id, product_name="Rice", payment_terms="100% advance", stage="Negotiation")
    db.add(deal); db.commit()
    with pytest.raises(HTTPException) as error:
        update_deal_stage(deal.deal_id, StageTransitionRequest(new_stage="Order Confirmed"), db)
    assert error.value.status_code == 409
    assert deal.stage == "Negotiation"

def test_invoice_requires_real_exporter_inputs():
    with pytest.raises(ValidationError):
        ProformaInvoiceCreate(deal_id="test")

def test_invoice_recomputes_and_checks_line_total():
    item = InvoiceItem(description="Rice", hs_code="100630", quantity=3, unit="KG", unit_price=0.1)
    assert item.total_amount == 0.3
    with pytest.raises(ValidationError):
        InvoiceItem(description="Rice", hs_code="100630", quantity=3, unit="KG", unit_price=0.1, total_amount=999)

def test_email_units_and_html_are_safe(db, buyer):
    product = ProductProfile(profile_id="fixture", product_name="<script>alert(1)</script>", product_category="Textiles", origin_country="India", target_price_min=3.4, price_unit="KG", currency="USD", certifications=[])
    draft = compose_grounded_email(buyer, product)
    assert "/ KG" in draft["body_text"]
    assert "/ MT" not in draft["body_text"]
    assert "<script>" not in draft["body_html"]
    assert "DGFT" not in draft["body_text"]

def test_gemini_is_called_and_output_is_constrained(db, buyer, monkeypatch):
    import httpx
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fixture-key")
    calls = []
    def post(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, request=httpx.Request("POST", url), json={"candidates": [{"content": {"parts": [{"text": json.dumps({"opening": 1, "closing": 2})}]}}]})
    monkeypatch.setattr(httpx, "post", post)
    product = ProductProfile(profile_id="fixture-ai", product_name="Rice", product_category="Rice", origin_country="India", certifications=[])
    draft = compose_grounded_email(buyer, product)
    assert calls and "generateContent" in calls[0]
    assert "Gemini" in draft["grounding_evidence"][0]

def test_no_synthetic_discovery_padding():
    from app.services.lead_discovery_crawler import LeadDiscoveryCrawler
    assert LeadDiscoveryCrawler()._generate_directory_leads("unknown", "unknown", 50) == []
