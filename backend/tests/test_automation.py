import uuid
from datetime import timedelta
import pytest
from fastapi import HTTPException
from app.core.database import init_db, SessionLocal
from app.core.config import settings
from app.models.automation import AutomationPolicy, AutomationState, AutomationRun
from app.models.product_profile import ProductProfile
from app.models.lead import Lead
from app.models.evidence import ReviewedEvidence
from app.models.outreach import OutreachEmail, SuppressionList
from app.api.automation import CampaignCreate, Authorization, create_campaign, authorize, pause, preview
from app.services.automation_service import run_cycle, dispatch_permission, utcnow, import_feed

@pytest.fixture
def setup(monkeypatch):
    init_db()
    db = SessionLocal()
    db.query(AutomationPolicy).update({"status": "Paused"})
    state = db.get(AutomationState, 1)
    state.enabled, state.last_cycle_at, state.lease_until = False, None, None
    monkeypatch.setattr(settings, "EXPORTER_NAME", "Fixture Exporter")
    monkeypatch.setattr(settings, "OUTREACH_ENABLED", False)
    monkeypatch.setattr(settings, "BUYER_FEED_URL", "")
    uid = uuid.uuid4().hex
    product = ProductProfile(profile_id=uid, product_name="Rice", product_category="Rice", specifications="Fixture declared rice specification", origin_country="India", export_readiness=True, is_active=True, currency="USD", price_unit="MT", target_countries=["Germany"], excluded_countries=[], certifications=[])
    db.add(product); db.commit()
    yield db, product
    state = db.get(AutomationState, 1)
    state.enabled = False
    db.commit(); db.close()

def buyer(db):
    uid = uuid.uuid4().hex
    lead = Lead(lead_id=uid, company_name="Fixture Rice Buyer " + uid, country="Germany", city="Hamburg", product_category="Rice", business_email=uid + "@buyer.de", contact_name="Fixture Buyer", job_title="Procurement Director", phone_number="123456", source="Fixture documented source", source_url="https://buyer.de/record", import_evidence="Fixture documented rice import activity", verification_status="Verified", buyer_score=100, risk_level="LOW", payment_risk_score=0, last_verified=utcnow(), outreach_status="Not Contacted", pipeline_stage="Qualified", dedup_hash=uid)
    db.add(lead)
    for category in ["identity", "imports"]:
        db.add(ReviewedEvidence(lead_id=uid, category=category, source_url="https://buyer.de/record", document_reference="Fixture source document 123", finding="Fixture reviewer checked the source document.", reviewed_by="fixture"))
    db.commit()
    return lead

def campaign(db, product, limit=2):
    data = create_campaign(CampaignCreate(name="Fixture campaign", product_id=product.profile_id, countries=["Germany"], daily_limit=limit), db)
    authorize(data["id"], Authorization(confirm=True), db)
    return db.get(AutomationPolicy, data["id"])

def enable(db):
    db.get(AutomationState, 1).enabled = True
    db.commit()

def test_paused_worker_has_no_side_effects(setup):
    db, product = setup
    before = db.query(AutomationRun).count()
    assert run_cycle(db)["status"] == "Paused"
    assert db.query(AutomationRun).count() == before

def test_campaign_requires_explicit_product_review(setup):
    db, product = setup
    product.export_readiness = False; db.commit()
    data = create_campaign(CampaignCreate(name="Fixture draft", product_id=product.profile_id, countries=["Germany"]), db)
    with pytest.raises(HTTPException):
        authorize(data["id"], Authorization(confirm=True), db)
    assert db.get(AutomationPolicy, data["id"]).status == "Draft"

def test_three_message_previews_do_not_send(setup):
    db, product = setup
    policy = campaign(db, product)
    data = preview(policy.id, db)
    assert len(data["touches"]) == 3
    assert "{buyer company}" in data["touches"][0]["subject"]
    assert db.query(OutreachEmail).filter_by(campaign_id=policy.campaign_id).count() == 0

def test_cycle_drafts_within_limit_and_never_simulates_send(setup):
    db, product = setup
    policy = campaign(db, product)
    for _ in range(3): buyer(db)
    enable(db)
    result = run_cycle(db, force=True)
    assert result["status"] == "Completed"
    assert result["drafted"] == 2 and result["sent"] == 0
    emails = db.query(OutreachEmail).filter_by(campaign_id=policy.campaign_id).all()
    assert all(e.status == "Approved" and e.sent_at is None and e.approval_mode == "Campaign" for e in emails)
    assert run_cycle(db, force=True)["drafted"] == 0

def test_product_changes_invalidate_authorization(setup):
    db, product = setup
    policy = campaign(db, product)
    buyer(db); enable(db)
    product.specifications = "Changed commercial specification"; db.commit()
    result = run_cycle(db, force=True)
    assert result["drafted"] == 0
    assert any(b["id"] == policy.id and "changed" in b["reason"] for b in result["blocked_campaigns"])

def test_paused_campaign_blocks_existing_approved_mail(setup):
    db, product = setup
    policy = campaign(db, product)
    buyer(db); enable(db); run_cycle(db, force=True)
    email = db.query(OutreachEmail).filter_by(campaign_id=policy.campaign_id).first()
    assert dispatch_permission(db, email) is None
    pause(policy.id, db)
    assert "paused" in dispatch_permission(db, email)

def test_changed_message_invalidates_campaign_approval(setup):
    db, product = setup
    policy = campaign(db, product)
    buyer(db); enable(db); run_cycle(db, force=True)
    email = db.query(OutreachEmail).filter_by(campaign_id=policy.campaign_id).first()
    email.body_text += " Invented claim"; db.commit()
    assert "Draft changed" in dispatch_permission(db, email)

def test_stale_buyer_evidence_prevents_automation(setup):
    db, product = setup
    policy = campaign(db, product)
    lead = buyer(db)
    lead.last_verified = utcnow() - timedelta(days=31); db.commit()
    enable(db)
    run_cycle(db, force=True)
    assert not db.query(OutreachEmail).filter_by(campaign_id=policy.campaign_id, lead_id=lead.lead_id).first()

def test_suppressed_buyer_is_excluded(setup):
    db, product = setup
    policy = campaign(db, product)
    lead = buyer(db)
    db.add(SuppressionList(email=lead.business_email, reason="Fixture opt-out")); db.commit()
    enable(db); run_cycle(db, force=True)
    assert not db.query(OutreachEmail).filter_by(campaign_id=policy.campaign_id, lead_id=lead.lead_id).first()

def test_worker_lease_prevents_overlapping_runs(setup):
    db, _ = setup
    enable(db)
    db.get(AutomationState, 1).lease_until = utcnow() + timedelta(minutes=5)
    db.commit()
    assert run_cycle(db, force=True)["status"] == "Already running"

def test_interval_is_persisted_across_worker_restarts(setup):
    db, _ = setup
    enable(db)
    run_cycle(db)
    assert run_cycle(db)["status"] == "Not due"

def test_feed_requires_public_https_and_never_uses_http(setup, monkeypatch):
    db, _ = setup
    monkeypatch.setattr(settings, "BUYER_FEED_URL", "http://127.0.0.1/records")
    with pytest.raises(ValueError):
        import_feed(db)
