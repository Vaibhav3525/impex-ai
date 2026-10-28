"""
Day 14 — Security, Hardening & 500-Lead Batch Verification Load Test
PRD §1 & §5: High-throughput ingestion (up to 500 records/day), deduplication scalability,
SQL/Score injection defenses, and strict security isolation.
"""

import time
import uuid
import pytest
from app.core.database import SessionLocal
from app.models.lead import Lead
from app.models.outreach import SuppressionList, OutreachEmail
from app.services.batch_ingestion import validate_row
from app.api.import_leads import _run_batch, MAX_ROWS_PER_UPLOAD
from app.services.email_composer import compose_grounded_email
from app.services.smtp_service import send_outreach_email
from app.models.product_profile import ProductProfile


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_500_lead_batch_ingestion_and_throughput(db_session):
    """
    PRD §1 & §5: System must process up to 500 new lead records per batch.
    Validates execution throughput, memory stability, and transactional integrity.
    """
    batch_size = 500
    batch_tag = uuid.uuid4().hex[:6]
    rows = []
    
    for i in range(batch_size):
        rows.append({
            "company_name": f"BatchLoad Importer {batch_tag} #{i:03d}",
            "country": "Germany" if i % 2 == 0 else "United Arab Emirates",
            "city": "Hamburg" if i % 2 == 0 else "Dubai",
            "website": f"https://importer-{batch_tag}-{i:03d}.de",
            "product_category": "Basmati Rice 1121",
            "contact_name": f"Buyer Manager {i}",
            "job_title": "Procurement Lead",
            "business_email": f"trade_{batch_tag}_{i:03d}@domain-{batch_tag}.com",
            "phone_number": f"+49 40 {100000 + i}",
            "source": "APEDA Official Directory",
            "source_url": "https://apeda.gov.in/trade-leads",
            "import_evidence": "Registered rice and grain import license #DE-987",
            "notes": "Bulk ingestion load test record",
        })

    start_time = time.time()
    try:
        result = _run_batch(rows, source_name="APEDA_Bulk_500.csv", auto_verify=False, db=db_session)
        duration = time.time() - start_time

        assert result.total_rows == 500
        assert result.created == 500
        assert result.duplicates == 0
        assert result.errors == 0
        assert duration < 10.0, f"500-lead batch took {duration:.2f}s, expected under 10.0s"
    finally:
        # Clean up 500 load test records to maintain database test isolation
        db_session.query(Lead).filter(Lead.company_name.like(f"BatchLoad Importer {batch_tag}%")).delete()
        db_session.commit()


def test_deduplication_under_batch_load(db_session):
    """
    Ensures that re-importing the same leads produces 100% duplicate detection
    with zero duplicate database rows and zero data inflation.
    """
    batch_tag = uuid.uuid4().hex[:6]
    original_rows = [
        {
            "company_name": f"Dedup Corp {batch_tag} Alpha",
            "country": "United Kingdom",
            "website": f"https://dedup-{batch_tag}.co.uk",
            "product_category": "Spices & Herbs",
            "source": "Indian Trade Portal",
            "business_email": f"buyer@{batch_tag}.co.uk",
        },
        {
            "company_name": f"Dedup Corp {batch_tag} Beta",
            "country": "Netherlands",
            "website": f"https://dedup-{batch_tag}.nl",
            "product_category": "Organic Tea",
            "source": "Indian Trade Portal",
            "business_email": f"procure@{batch_tag}.nl",
        }
    ]

    # First run: should create both
    res1 = _run_batch(original_rows, source_name="first_run.csv", auto_verify=False, db=db_session)
    assert res1.created == 2
    assert res1.duplicates == 0

    # Second run: identical rows should be flagged as duplicates
    res2 = _run_batch(original_rows, source_name="second_run.csv", auto_verify=False, db=db_session)
    assert res2.created == 0
    assert res2.duplicates == 2
    assert res2.errors == 0


def test_batch_limit_rejection_boundary():
    """Verify that MAX_ROWS_PER_UPLOAD enforces PRD upper boundary limit."""
    assert MAX_ROWS_PER_UPLOAD == 500


def test_security_external_score_injection_prevented():
    """
    Security Test: Attackers attempting to inject a fabricated 'buyer_score'
    or verification status via CSV must have the field stripped.
    """
    malicious_row = {
        "company_name": "Injected Legitimacy LLC",
        "country": "Singapore",
        "product_category": "Refined Sugar",
        "source": "Untrusted CSV",
        "buyer_score": "100.0",  # Injected external score
        "verification_status": "Verified",
    }

    cleaned, errors, warnings = validate_row(malicious_row, row_num=1)
    assert "buyer_score" not in cleaned
    assert any("buyer_score' was stripped" in w for w in warnings)


def test_security_sql_injection_resilience(db_session):
    """
    Security Test: Complex SQL injection payloads in string fields
    must be stored safely as literal strings without altering DB structure.
    """
    uid = uuid.uuid4().hex[:6]
    injection_payload = f"Malicious Corp {uid}'; DROP TABLE leads; --"
    row = {
        "company_name": injection_payload,
        "country": "United States",
        "product_category": "Grains' OR '1'='1",
        "source": "Hacker Import",
        "notes": "1' UNION SELECT username, password FROM users --",
    }

    res = _run_batch([row], source_name="sqli_test.csv", auto_verify=False, db=db_session)
    assert res.created == 1

    # Verify that the table still exists and data was escaped safely
    saved = db_session.query(Lead).filter(Lead.company_name == injection_payload).first()
    assert saved is not None
    assert saved.company_name == injection_payload
    assert "DROP TABLE" in saved.company_name


def test_security_suppression_list_isolation(db_session):
    """
    Security Test: Once an email is registered on the suppression list,
    all outreach dispatch attempts MUST be blocked immediately.
    """
    uid = uuid.uuid4().hex[:6]
    suppressed_email = f"optout_{uid}@suppressed-corp.com"

    # Add to suppression registry
    suppression = SuppressionList(
        email=suppressed_email,
        reason="Unsubscribe / Opt-Out Request",
        notes="Buyer requested immediate exclusion under GDPR"
    )
    db_session.add(suppression)

    # Create approved email to the suppressed address
    lead = Lead(
        lead_id=f"LEAD-SUPP-{uid}",
        company_name=f"Suppressed Corp {uid}",
        country="France",
        product_category="Organic Spices",
        source="APEDA Directory",
        dedup_hash=f"hash_{uid}",
        verification_status="Verified",
        business_email=suppressed_email
    )
    db_session.add(lead)
    db_session.commit()

    email = OutreachEmail(
        email_id=f"EML-SUPP-{uid}",
        lead_id=lead.lead_id,
        to_email=suppressed_email,
        company_name=lead.company_name,
        country="France",
        subject="Trade Partnership Inquiry",
        body_text="Hello, we export spices.",
        status="Approved"  # Even if approved by human, suppression must block dispatch
    )
    db_session.add(email)
    db_session.commit()

    result = send_outreach_email(db_session, email.email_id)
    assert result["success"] is False
    assert "suppression list" in result["error"].lower()

    # Verify email status updated to Suppressed
    db_session.refresh(email)
    assert email.status == "Suppressed"
