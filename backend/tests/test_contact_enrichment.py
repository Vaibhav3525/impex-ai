import pytest
from app.services.contact_enrichment import extract_contacts, scan_company, _validate_url, enrich_contact_batch
from app.core.database import init_db, SessionLocal
from app.services.lead_service import ingest_lead
from app.schemas.lead import LeadCreate


def test_contact_extraction_has_exact_source_and_ignores_script_numbers():
    html = b'''<script>const x="fake@asset.test";const n="0123456789";</script>
      <a href="mailto:info@buyer.test?subject=Hello">Email</a>
      <a href="tel:+44-1234-567890">Call</a>
      <a href="/contact">Contact</a><a href="https://other.test/contact">Other</a>
      <p>privacy@buyer.test</p>'''
    contacts, links = extract_contacts(html, "https://buyer.test/")
    assert {c["value"] for c in contacts} == {"info@buyer.test", "+44-1234-567890"}
    assert all(c["source_url"] == "https://buyer.test/" for c in contacts)
    assert links == ["https://buyer.test/contact"]


def test_company_scan_blocks_private_hosts_and_offsite_redirects(monkeypatch):
    monkeypatch.setattr("app.services.contact_enrichment.socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError):
        _validate_url("https://buyer.test", "buyer.test")
    with pytest.raises(ValueError):
        _validate_url("https://internal.test/contact", "buyer.test")
    assert scan_company(None)["status"] == "Company website needed"


def test_enrichment_preserves_operator_contacts_and_records_progress(monkeypatch):
    init_db()
    with SessionLocal() as db:
        lead, _ = ingest_lead(db, LeadCreate(
            company_name="Enrichment Test Ltd", country="United Kingdom", website="https://fixture.test",
            product_category="Rice", source="The Rice Association", business_email="approved@fixture.test",
        ))
        monkeypatch.setattr("app.services.contact_enrichment.scan_company", lambda _: {
            "status": "Published contacts found", "checked_at": "2026-11-25T00:00:00Z",
            "contacts": [{"type": "email", "value": "sales@fixture.test", "source_url": "https://fixture.test/contact"}],
        })
        result = enrich_contact_batch(db, limit=4)
        assert result["processed"] == 1
        db.refresh(lead)
        assert lead.business_email == "approved@fixture.test"
        assert lead.verification_status == "Unverified"
        assert lead.contact_enrichment["contacts"][0]["source_url"] == "https://fixture.test/contact"
        assert enrich_contact_batch(db)["processed"] == 0


def test_new_website_and_failed_scan_retry_once_per_cutoff(monkeypatch):
    from datetime import datetime, timezone, timedelta
    from app.models.lead import Lead

    init_db()
    with SessionLocal() as db:
        lead, _ = ingest_lead(db, LeadCreate(
            company_name="Retry Website Fixture", country="Germany", product_category="Spices",
            source="European Spice Association",
        ))
        lead.contact_enrichment = {"status": "Company website needed", "checked_at": "2026-01-01T00:00:00Z",
                                   "scanned_website": None, "website_evidence": {"source_url": "https://directory.test/member"}}
        lead.website = "https://retry.test"
        db.commit()
        cutoff = datetime.now(timezone.utc)
        def scanned(website):
            return {"scanned_website": website, "checked_at": datetime.now(timezone.utc).isoformat(),
                    "status": "Website scan incomplete", "contacts": [], "pages": [], "errors": ["ReadTimeout"]}
        monkeypatch.setattr("app.services.contact_enrichment.scan_company", scanned)
        assert enrich_contact_batch(db)["processed"] == 1
        db.refresh(lead)
        assert lead.contact_enrichment["website_evidence"]["source_url"] == "https://directory.test/member"
        assert enrich_contact_batch(db, retry_before=cutoff)["processed"] == 0
        assert enrich_contact_batch(db, retry_before=datetime.now(timezone.utc) + timedelta(seconds=1))["processed"] == 1
