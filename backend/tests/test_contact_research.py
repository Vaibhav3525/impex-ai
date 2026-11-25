import pytest
from fastapi import HTTPException
from app.api.discovery import ContactResearch, save_contact_research
from app.core.database import init_db, SessionLocal
from app.schemas.lead import LeadCreate
from app.services.lead_service import ingest_lead


def test_reviewed_contact_keeps_provenance_and_does_not_approve_lead():
    init_db()
    with SessionLocal() as db:
        lead, _ = ingest_lead(db, LeadCreate(company_name="Reviewed Contact Fixture", country="UK",
            website="https://fixture.example.org", product_category="Tea", source="Public source"))
        lead.contact_enrichment = {"website_evidence": {"finding": "Existing website research"}}
        db.commit()
        original_hash = lead.dedup_hash
        request = ContactResearch(business_email=" Sales@buyer.org ",
            source_url="https://buyer.org/contact", finding="The company publishes this exact sales address on its contact page.")
        save_contact_research(lead.lead_id, request, db)
        save_contact_research(lead.lead_id, request, db)
        db.refresh(lead)
        assert lead.business_email == "sales@buyer.org"
        assert lead.dedup_hash == original_hash
        assert lead.verification_status == "Unverified" and lead.buyer_score == 0
        assert lead.contact_enrichment["website_evidence"]["finding"] == "Existing website research"
        assert len(lead.contact_enrichment["reviewed_contacts"]) == 1
        assert lead.contact_enrichment["reviewed_contacts"][0]["source_url"] == "https://buyer.org/contact"
        with pytest.raises(HTTPException) as conflict:
            save_contact_research(lead.lead_id, request.model_copy(update={"business_email": "different@buyer.org"}), db)
        assert conflict.value.status_code == 409
        for email, url in [("not-an-email", "https://buyer.org/contact"), ("sales@buyer.org", "https://example.com/contact")]:
            with pytest.raises(HTTPException) as invalid:
                save_contact_research(lead.lead_id, ContactResearch(business_email=email,source_url=url,finding=request.finding), db)
            assert invalid.value.status_code == 422
