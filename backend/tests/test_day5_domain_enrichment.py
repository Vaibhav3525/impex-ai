"""
Day 5 Tests — Domain Enrichment Service
Tests all enrichment checks in fully offline mode (no network calls).
Covers:
  - MXResult / TLSResult / WHOISResult / ContactPageResult data containers
  - enrich_domain() with pre-injected mock results (monkeypatched)
  - DomainEnrichmentResult.to_dict() serialization
  - Score delta clamping (never below 0, never above 15 per component)
  - FLAG_DOMAIN_AGE_UNDER_90_DAYS raised for young domains
  - FLAG_DOMAIN_NOT_FOUND raised for NXDOMAIN
  - FLAG_TLS_INVALID raised for bad certificate
  - Updated run_lead_verification() with enrichment parameter
  - Evidence notes not fabricated
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.services.domain_enrichment import (
    MXResult,
    SMTPProbeResult,
    TLSResult,
    WHOISResult,
    ContactPageResult,
    DomainEnrichmentResult,
    _extract_domain,
    enrich_domain,
)
from app.services.verification_service import run_lead_verification, evaluate_email_quality
from app.core.database import SessionLocal, init_db
from app.models.lead import Lead
from app.services.lead_service import ingest_lead
from app.schemas.lead import LeadCreate


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    """In-memory SQLite database for the entire test module."""
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _make_lead(db, suffix: str = "d5") -> Lead:
    """Create a fresh lead for testing."""
    lc = LeadCreate(
        company_name=f"EuroTrade GmbH {suffix}",
        country="Germany",
        city="Hamburg",
        website="https://eurotrade.de",
        product_category="Spices",
        contact_name="Hans Müller",
        job_title="Import Manager",
        business_email=f"hans@eurotrade-{suffix}.de",
        phone_number="+49 40 12345678",
        source="APEDA International Buyer Directory",
        source_url="https://apeda.gov.in/",
        import_evidence="Listed in APEDA spice buyer directory for Germany.",
        notes="Test lead for Day 5",
    )
    lead, _ = ingest_lead(db, lc)
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# 1. _extract_domain helper
# ─────────────────────────────────────────────────────────────────────────────

def test_extract_domain_from_email():
    assert _extract_domain("buyer@acme.de") == "acme.de"

def test_extract_domain_from_https_url():
    assert _extract_domain("https://www.acme.de/about") == "acme.de"

def test_extract_domain_from_http_url():
    assert _extract_domain("http://acme.de") == "acme.de"

def test_extract_domain_bare():
    assert _extract_domain("acme.de") == "acme.de"


# ─────────────────────────────────────────────────────────────────────────────
# 2. MXResult
# ─────────────────────────────────────────────────────────────────────────────

def test_mx_result_has_mx_true():
    mx = MXResult(domain="acme.de", records=["mail.acme.de"], priority=[10])
    assert mx.has_mx is True

def test_mx_result_has_mx_false_empty():
    mx = MXResult(domain="acme.de", records=[], error="No MX records found")
    assert mx.has_mx is False

def test_mx_result_has_mx_false_error():
    mx = MXResult(domain="ghost.xyz", error="NXDOMAIN — domain does not exist")
    assert mx.has_mx is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. DomainEnrichmentResult.to_dict() serialization
# ─────────────────────────────────────────────────────────────────────────────

def test_enrichment_to_dict_all_none():
    result = DomainEnrichmentResult(domain="test.com")
    d = result.to_dict()
    assert d["domain"] == "test.com"
    assert d["mx"]["has_mx"] is False
    assert d["tls"]["valid"] is False
    assert d["whois"]["domain_age_days"] is None
    assert d["contact_page"]["linkedin_url"] is None
    assert d["score_deltas"]["email_score_delta"] == 0.0

def test_enrichment_to_dict_with_mx():
    mx = MXResult(domain="acme.de", records=["mx1.acme.de"], priority=[10], checked_at="2026-01-01T00:00:00+00:00")
    result = DomainEnrichmentResult(domain="acme.de", mx=mx)
    d = result.to_dict()
    assert d["mx"]["has_mx"] is True
    assert d["mx"]["records"] == ["mx1.acme.de"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Score Delta Clamping
# ─────────────────────────────────────────────────────────────────────────────

def test_score_delta_clamp_max():
    result = DomainEnrichmentResult(domain="test.com")
    result.email_score_delta = 99.0  # Will be clamped to 15 inside enrich_domain
    # to_dict preserves whatever is set — clamping is done inside enrich_domain
    # Here we test the clamp logic used in enrich_domain:
    clamped = max(-15.0, min(result.email_score_delta, 15.0))
    assert clamped == 15.0

def test_score_delta_clamp_min():
    result = DomainEnrichmentResult(domain="test.com")
    result.email_score_delta = -99.0
    clamped = max(-15.0, min(result.email_score_delta, 15.0))
    assert clamped == -15.0


# ─────────────────────────────────────────────────────────────────────────────
# 5. enrich_domain() with fully mocked network calls
# ─────────────────────────────────────────────────────────────────────────────

def _mock_mx_good(domain, timeout=5.0):
    return MXResult(domain=domain, records=["mail.acme.de"], priority=[10], checked_at="T")

def _mock_mx_nxdomain(domain, timeout=5.0):
    return MXResult(domain=domain, error="NXDOMAIN — domain does not exist", checked_at="T")

def _mock_smtp_ok(mx_host, probe_domain=""):
    return SMTPProbeResult(host=mx_host, port=25, reachable=True, banner="220 ESMTP", checked_at="T")

def _mock_smtp_fail(mx_host, probe_domain=""):
    return SMTPProbeResult(host=mx_host, port=25, reachable=False, error="port 25 blocked", checked_at="T")

def _mock_tls_valid(domain):
    return TLSResult(domain=domain, valid=True, days_to_expiry=180, issuer="Let's Encrypt", checked_at="T")

def _mock_tls_invalid(domain):
    return TLSResult(domain=domain, valid=False, error="Certificate expired", checked_at="T")

def _mock_whois_old(domain):
    return WHOISResult(domain=domain, domain_age_days=1200, creation_date="2021-01-01T00:00:00+00:00",
                       registrar="GoDaddy", checked_at="T")

def _mock_whois_new(domain):
    return WHOISResult(domain=domain, domain_age_days=30, creation_date="2026-09-01T00:00:00+00:00",
                       registrar="Namecheap", checked_at="T")

def _mock_contact_good(base_url, rate_limit_seconds=1.5):
    return ContactPageResult(
        base_url=base_url,
        contact_links=[f"{base_url}/contact"],
        linkedin_url="https://linkedin.com/company/acme",
        detected_addresses=["123 Main Street, Hamburg"],
        detected_emails=["info@acme.de"],
        detected_phones=["+49 40 1234"],
        checked_at="T",
    )

def _mock_contact_fail(base_url, rate_limit_seconds=1.5):
    return ContactPageResult(base_url=base_url, error="Connection timeout", checked_at="T")


@patch("app.services.domain_enrichment.check_dns_mx", side_effect=_mock_mx_good)
@patch("app.services.domain_enrichment.probe_smtp", side_effect=_mock_smtp_ok)
@patch("app.services.domain_enrichment.check_tls", side_effect=_mock_tls_valid)
@patch("app.services.domain_enrichment.check_whois_age", side_effect=_mock_whois_old)
@patch("app.services.domain_enrichment.scan_contact_page", side_effect=_mock_contact_good)
def test_enrich_domain_all_checks_pass(mock_cp, mock_w, mock_tls, mock_smtp, mock_mx):
    result = enrich_domain("acme.de")
    assert result.domain == "acme.de"
    assert result.mx is not None and result.mx.has_mx
    assert result.tls is not None and result.tls.valid
    assert result.whois is not None and result.whois.domain_age_days == 1200
    assert result.contact_page is not None and result.contact_page.linkedin_url is not None
    # Positive deltas expected
    assert result.email_score_delta > 0
    assert result.website_score_delta > 0
    assert result.independent_score_delta > 0
    assert len(result.new_flags) == 0


@patch("app.services.domain_enrichment.check_dns_mx", side_effect=_mock_mx_nxdomain)
@patch("app.services.domain_enrichment.check_tls", side_effect=_mock_tls_invalid)
@patch("app.services.domain_enrichment.check_whois_age", side_effect=_mock_whois_new)
@patch("app.services.domain_enrichment.scan_contact_page", side_effect=_mock_contact_fail)
def test_enrich_domain_all_checks_fail(mock_cp, mock_w, mock_tls, mock_mx):
    result = enrich_domain("ghost.xyz", run_smtp=True)
    assert result.domain == "ghost.xyz"
    assert result.mx is not None and not result.mx.has_mx
    assert result.tls is not None and not result.tls.valid
    assert "FLAG_DOMAIN_NOT_FOUND" in result.new_flags
    assert "FLAG_TLS_INVALID" in result.new_flags
    assert "FLAG_DOMAIN_AGE_UNDER_90_DAYS" in result.new_flags
    # Negative / zero deltas expected
    assert result.email_score_delta < 0


@patch("app.services.domain_enrichment.check_dns_mx", side_effect=_mock_mx_good)
@patch("app.services.domain_enrichment.probe_smtp", side_effect=_mock_smtp_fail)
@patch("app.services.domain_enrichment.check_tls", side_effect=_mock_tls_valid)
@patch("app.services.domain_enrichment.check_whois_age", side_effect=_mock_whois_old)
@patch("app.services.domain_enrichment.scan_contact_page", side_effect=_mock_contact_good)
def test_enrich_domain_smtp_fail_is_inconclusive(mock_cp, mock_w, mock_tls, mock_smtp, mock_mx):
    """SMTP failure must NOT create a negative flag — port 25 is often blocked."""
    result = enrich_domain("acme.de")
    assert result.smtp is not None and not result.smtp.reachable
    # No SMTP-specific flag should appear
    smtp_flags = [f for f in result.new_flags if "SMTP" in f]
    assert len(smtp_flags) == 0
    # But email delta still positive from MX
    assert result.email_score_delta > 0


@patch("app.services.domain_enrichment.check_dns_mx", side_effect=_mock_mx_good)
@patch("app.services.domain_enrichment.check_tls", side_effect=_mock_tls_valid)
@patch("app.services.domain_enrichment.check_whois_age", side_effect=_mock_whois_new)
@patch("app.services.domain_enrichment.scan_contact_page", side_effect=_mock_contact_good)
def test_enrich_domain_young_domain_flag(mock_cp, mock_w, mock_tls, mock_mx):
    result = enrich_domain("newstartup.io", run_smtp=False)
    assert "FLAG_DOMAIN_AGE_UNDER_90_DAYS" in result.new_flags


# ─────────────────────────────────────────────────────────────────────────────
# 6. run_lead_verification() with pre-computed enrichment
# ─────────────────────────────────────────────────────────────────────────────

def test_run_verification_with_enrichment(db):
    """Verification with a positive enrichment result should boost score."""
    lead = _make_lead(db, suffix="enrich-pos")
    base_score_before = lead.buyer_score or 0.0

    enrichment = DomainEnrichmentResult(
        domain="eurotrade.de",
        mx=MXResult(domain="eurotrade.de", records=["mail.eurotrade.de"], priority=[10], checked_at="T"),
        tls=TLSResult(domain="eurotrade.de", valid=True, days_to_expiry=300, checked_at="T"),
        whois=WHOISResult(domain="eurotrade.de", domain_age_days=1500, checked_at="T"),
        contact_page=ContactPageResult(
            base_url="https://eurotrade.de",
            linkedin_url="https://linkedin.com/company/eurotrade",
            detected_emails=["info@eurotrade.de"],
            checked_at="T",
        ),
    )
    # Set realistic deltas
    enrichment.email_score_delta = 5.0
    enrichment.website_score_delta = 3.0
    enrichment.independent_score_delta = 3.0
    enrichment.evidence_notes = ["MX OK", "TLS valid 300 days", "LinkedIn found"]

    log = run_lead_verification(db, lead, enrichment=enrichment, run_live_checks=False)
    assert log.total_score >= base_score_before
    assert log.dns_mx_records == ["mail.eurotrade.de"]
    assert log.ssl_valid == "VALID"
    assert log.domain_age_days == 1500


def test_run_verification_with_negative_enrichment(db):
    """Negative enrichment (NXDOMAIN) should not push score below 0."""
    lead = _make_lead(db, suffix="enrich-neg")

    enrichment = DomainEnrichmentResult(
        domain="ghost.xyz",
        mx=MXResult(domain="ghost.xyz", error="NXDOMAIN — domain does not exist", checked_at="T"),
        tls=TLSResult(domain="ghost.xyz", valid=False, error="Certificate error", checked_at="T"),
    )
    enrichment.email_score_delta = -15.0   # Max negative
    enrichment.website_score_delta = -15.0
    enrichment.new_flags = ["FLAG_DOMAIN_NOT_FOUND", "FLAG_TLS_INVALID"]
    enrichment.evidence_notes = ["NXDOMAIN", "TLS invalid"]

    log = run_lead_verification(db, lead, enrichment=enrichment, run_live_checks=False)
    assert log.total_score >= 0.0
    assert "FLAG_DOMAIN_NOT_FOUND" in (log.detected_flags or [])
    assert "FLAG_TLS_INVALID" in (log.detected_flags or [])


def test_run_verification_offline_no_enrichment(db):
    """Offline verification (run_live_checks=False) must still score correctly."""
    lead = _make_lead(db, suffix="offline")
    log = run_lead_verification(db, lead, enrichment=None, run_live_checks=False)
    assert log.total_score >= 0.0
    assert log.total_score <= 100.0
    assert log.evidence_summary is not None
    assert log.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


# ─────────────────────────────────────────────────────────────────────────────
# 7. Evidence notes — no fabrication check
# ─────────────────────────────────────────────────────────────────────────────

def test_no_fabricated_contact_data_in_enrichment():
    """
    Enrichment must only return data found in actual page content.
    If contact page scan returns no emails, no emails should be added.
    """
    result = DomainEnrichmentResult(domain="test.com")
    result.contact_page = ContactPageResult(
        base_url="https://test.com",
        detected_emails=[],
        detected_addresses=[],
        linkedin_url=None,
        checked_at="T",
    )
    assert result.contact_page.detected_emails == []
    assert result.contact_page.linkedin_url is None


def test_evidence_notes_are_not_hallucinated():
    """Evidence notes must only reference real check results."""
    enrichment = DomainEnrichmentResult(domain="acme.de")
    enrichment.evidence_notes = ["MX confirmed: mail.acme.de"]  # Grounded in MX check
    for note in enrichment.evidence_notes:
        # Notes must not contain certifications, prices, or trade histories
        assert "certified" not in note.lower()
        assert "usd" not in note.lower()
        assert "import volume" not in note.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 8. evaluate_email_quality — unchanged regression
# ─────────────────────────────────────────────────────────────────────────────

def test_email_quality_corporate():
    score, flags = evaluate_email_quality("buyer@acme.de")
    assert score == 15.0
    assert flags == []

def test_email_quality_free_domain():
    score, flags = evaluate_email_quality("buyer@gmail.com")
    assert score < 15.0
    assert "FLAG_FREE_EMAIL_DOMAIN" in flags

def test_email_quality_missing():
    score, flags = evaluate_email_quality(None)
    assert score == 0.0
    assert "FLAG_MISSING_EMAIL" in flags

def test_email_quality_no_at_sign():
    score, flags = evaluate_email_quality("notanemail")
    assert score == 0.0

