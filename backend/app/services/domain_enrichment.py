"""
Day 5 — Domain Enrichment Service
Performs live technical verification of a company domain:

  1. DNS MX lookup  — confirms the domain is mail-enabled
  2. SMTP handshake — port-25 EHLO probe (no message sent, no auth)
  3. TLS/SSL check  — certificate validity and days-to-expiry
  4. WHOIS age      — domain registration age in days
  5. Contact-page   — extract contact links, LinkedIn page, address hints

All checks are best-effort.  A failure in any single check does NOT
automatically disqualify a lead — it is recorded as evidence and fed
into the verification score delta returned from enrich_domain().

PRD constraints enforced here:
  - Never fabricate missing data.
  - Never store inferred data without labelling it as an inference.
  - All evidence carries a timestamp and source description.
"""

from __future__ import annotations

import re
import ssl
import socket
import smtplib
import time
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

import dns.resolver
import dns.exception
import httpx

try:
    import whois as python_whois  # python-whois package
    _WHOIS_AVAILABLE = True
except ImportError:
    _WHOIS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data Containers
# ---------------------------------------------------------------------------

@dataclass
class MXResult:
    """DNS MX lookup result."""
    domain: str
    records: list[str] = field(default_factory=list)   # e.g. ["mail.example.com"]
    priority: list[int] = field(default_factory=list)  # Corresponding priorities
    error: Optional[str] = None
    checked_at: str = ""

    @property
    def has_mx(self) -> bool:
        return bool(self.records)


@dataclass
class SMTPProbeResult:
    """Result of an SMTP EHLO handshake probe (no email sent)."""
    host: str
    port: int
    reachable: bool
    banner: Optional[str] = None
    error: Optional[str] = None
    checked_at: str = ""


@dataclass
class TLSResult:
    """TLS/SSL certificate check result."""
    domain: str
    valid: bool
    days_to_expiry: Optional[int] = None
    issuer: Optional[str] = None
    subject: Optional[str] = None
    error: Optional[str] = None
    checked_at: str = ""


@dataclass
class WHOISResult:
    """WHOIS domain registration result."""
    domain: str
    domain_age_days: Optional[int] = None
    creation_date: Optional[str] = None
    registrar: Optional[str] = None
    error: Optional[str] = None
    checked_at: str = ""


@dataclass
class ContactPageResult:
    """Results from scraping the company contact/about page."""
    base_url: str
    contact_links: list[str] = field(default_factory=list)  # /contact, /about, etc.
    linkedin_url: Optional[str] = None
    detected_addresses: list[str] = field(default_factory=list)
    detected_emails: list[str] = field(default_factory=list)
    detected_phones: list[str] = field(default_factory=list)
    error: Optional[str] = None
    checked_at: str = ""


@dataclass
class DomainEnrichmentResult:
    """Aggregated result of all domain enrichment checks."""
    domain: str
    mx: Optional[MXResult] = None
    smtp: Optional[SMTPProbeResult] = None
    tls: Optional[TLSResult] = None
    whois: Optional[WHOISResult] = None
    contact_page: Optional[ContactPageResult] = None

    # Computed score delta: how much to add / subtract from current email_score
    email_score_delta: float = 0.0
    website_score_delta: float = 0.0
    independent_score_delta: float = 0.0
    new_flags: list[str] = field(default_factory=list)
    evidence_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to a plain dict for API responses and DB storage."""
        return {
            "domain": self.domain,
            "mx": {
                "has_mx": self.mx.has_mx if self.mx else False,
                "records": self.mx.records if self.mx else [],
                "error": self.mx.error if self.mx else "not_checked",
                "checked_at": self.mx.checked_at if self.mx else "",
            },
            "smtp": {
                "reachable": self.smtp.reachable if self.smtp else False,
                "banner": self.smtp.banner if self.smtp else None,
                "error": self.smtp.error if self.smtp else "not_checked",
                "checked_at": self.smtp.checked_at if self.smtp else "",
            },
            "tls": {
                "valid": self.tls.valid if self.tls else False,
                "days_to_expiry": self.tls.days_to_expiry if self.tls else None,
                "issuer": self.tls.issuer if self.tls else None,
                "error": self.tls.error if self.tls else "not_checked",
                "checked_at": self.tls.checked_at if self.tls else "",
            },
            "whois": {
                "domain_age_days": self.whois.domain_age_days if self.whois else None,
                "creation_date": self.whois.creation_date if self.whois else None,
                "registrar": self.whois.registrar if self.whois else None,
                "error": self.whois.error if self.whois else "not_checked",
                "checked_at": self.whois.checked_at if self.whois else "",
            },
            "contact_page": {
                "linkedin_url": self.contact_page.linkedin_url if self.contact_page else None,
                "contact_links": self.contact_page.contact_links if self.contact_page else [],
                "detected_addresses": self.contact_page.detected_addresses if self.contact_page else [],
                "detected_emails": self.contact_page.detected_emails if self.contact_page else [],
                "detected_phones": self.contact_page.detected_phones if self.contact_page else [],
                "error": self.contact_page.error if self.contact_page else "not_checked",
                "checked_at": self.contact_page.checked_at if self.contact_page else "",
            },
            "score_deltas": {
                "email_score_delta": self.email_score_delta,
                "website_score_delta": self.website_score_delta,
                "independent_score_delta": self.independent_score_delta,
            },
            "new_flags": self.new_flags,
            "evidence_notes": self.evidence_notes,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_domain(url_or_email: str) -> str:
    """Extract bare domain from a URL or email address."""
    s = url_or_email.strip().lower()
    if "@" in s:
        return s.split("@")[-1]
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    return s.split("/")[0].split("?")[0].split("#")[0]


# ---------------------------------------------------------------------------
# Check 1: DNS MX Lookup
# ---------------------------------------------------------------------------

def check_dns_mx(domain: str, timeout: float = 5.0) -> MXResult:
    """
    Resolve MX records for *domain* using dnspython.
    A domain with at least one MX record has mail infrastructure —
    strong positive signal for a live corporate email address.
    """
    ts = _utc_now_str()
    try:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = timeout
        answers = resolver.resolve(domain, "MX")
        records = [str(r.exchange).rstrip(".") for r in answers]
        priorities = [r.preference for r in answers]
        return MXResult(
            domain=domain,
            records=records,
            priority=priorities,
            checked_at=ts,
        )
    except dns.resolver.NXDOMAIN:
        return MXResult(domain=domain, error="NXDOMAIN — domain does not exist", checked_at=ts)
    except dns.resolver.NoAnswer:
        return MXResult(domain=domain, error="No MX records found", checked_at=ts)
    except dns.exception.Timeout:
        return MXResult(domain=domain, error="DNS timeout", checked_at=ts)
    except Exception as exc:
        return MXResult(domain=domain, error=str(exc)[:200], checked_at=ts)


# ---------------------------------------------------------------------------
# Check 2: SMTP Handshake Probe (port 25, EHLO only — no email sent)
# ---------------------------------------------------------------------------

SMTP_PROBE_TIMEOUT = 8.0   # seconds
SMTP_PORT = 25


def probe_smtp(mx_host: str, probe_domain: str = "impex-verify.example.com") -> SMTPProbeResult:
    """
    Attempt an SMTP EHLO handshake with the MX host.
    This verifies the mail server is live and accepting connections.
    No email is sent.  The connection is closed immediately after EHLO.

    Note: Many cloud and ISP networks block outbound port 25.
    A failure here is not conclusive — log it and continue.
    """
    ts = _utc_now_str()
    try:
        with smtplib.SMTP(mx_host, SMTP_PORT, timeout=SMTP_PROBE_TIMEOUT) as smtp:
            banner = smtp.getwelcome().decode(errors="replace")[:200]
            smtp.ehlo(probe_domain)
            return SMTPProbeResult(
                host=mx_host, port=SMTP_PORT,
                reachable=True, banner=banner, checked_at=ts,
            )
    except smtplib.SMTPConnectError as e:
        return SMTPProbeResult(host=mx_host, port=SMTP_PORT, reachable=False,
                               error=f"SMTPConnectError: {e}", checked_at=ts)
    except ConnectionRefusedError:
        return SMTPProbeResult(host=mx_host, port=SMTP_PORT, reachable=False,
                               error="Connection refused (port 25 blocked?)", checked_at=ts)
    except TimeoutError:
        return SMTPProbeResult(host=mx_host, port=SMTP_PORT, reachable=False,
                               error="SMTP connection timeout", checked_at=ts)
    except OSError as e:
        return SMTPProbeResult(host=mx_host, port=SMTP_PORT, reachable=False,
                               error=str(e)[:200], checked_at=ts)
    except Exception as exc:
        return SMTPProbeResult(host=mx_host, port=SMTP_PORT, reachable=False,
                               error=str(exc)[:200], checked_at=ts)


# ---------------------------------------------------------------------------
# Check 3: TLS / SSL Certificate
# ---------------------------------------------------------------------------

TLS_PORT = 443
TLS_TIMEOUT = 8.0


def check_tls(domain: str) -> TLSResult:
    """
    Verify TLS certificate for *domain* on port 443.
    Returns validity, days to expiry, and issuer/subject info.
    An invalid or expired certificate is a negative signal.
    """
    ts = _utc_now_str()
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((domain, TLS_PORT), timeout=TLS_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                # Expiry
                not_after_str = cert.get("notAfter", "")
                if not_after_str:
                    not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
                    not_after = not_after.replace(tzinfo=timezone.utc)
                    days_left = (not_after - datetime.now(timezone.utc)).days
                else:
                    days_left = None

                # Issuer / Subject
                issuer_dict = dict(x[0] for x in cert.get("issuer", []))
                subject_dict = dict(x[0] for x in cert.get("subject", []))
                issuer_cn = issuer_dict.get("organizationName") or issuer_dict.get("commonName", "")
                subject_cn = subject_dict.get("commonName", "")

                return TLSResult(
                    domain=domain,
                    valid=True,
                    days_to_expiry=days_left,
                    issuer=issuer_cn[:100] if issuer_cn else None,
                    subject=subject_cn[:100] if subject_cn else None,
                    checked_at=ts,
                )
    except ssl.CertificateError as e:
        return TLSResult(domain=domain, valid=False, error=f"Certificate error: {e}", checked_at=ts)
    except ssl.SSLError as e:
        return TLSResult(domain=domain, valid=False, error=f"SSL error: {e}", checked_at=ts)
    except (socket.timeout, TimeoutError):
        return TLSResult(domain=domain, valid=False, error="TLS connection timeout", checked_at=ts)
    except (ConnectionRefusedError, socket.gaierror) as e:
        return TLSResult(domain=domain, valid=False, error=str(e)[:200], checked_at=ts)
    except Exception as exc:
        return TLSResult(domain=domain, valid=False, error=str(exc)[:200], checked_at=ts)


# ---------------------------------------------------------------------------
# Check 4: WHOIS Domain Age
# ---------------------------------------------------------------------------

def check_whois_age(domain: str) -> WHOISResult:
    """
    Query WHOIS to determine domain registration age.
    Domains registered < 90 days ago are flagged as potentially suspicious.
    Requires the `python-whois` package.
    """
    ts = _utc_now_str()
    if not _WHOIS_AVAILABLE:
        return WHOISResult(domain=domain, error="python-whois not installed", checked_at=ts)

    try:
        w = python_whois.whois(domain)
        creation = w.creation_date
        registrar = w.registrar

        # creation_date may be a list or a single datetime
        if isinstance(creation, list):
            creation = creation[0]

        age_days: Optional[int] = None
        creation_str: Optional[str] = None

        if isinstance(creation, datetime):
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - creation).days
            creation_str = creation.isoformat()

        if isinstance(registrar, list):
            registrar = registrar[0]

        return WHOISResult(
            domain=domain,
            domain_age_days=age_days,
            creation_date=creation_str,
            registrar=str(registrar)[:100] if registrar else None,
            checked_at=ts,
        )
    except Exception as exc:
        return WHOISResult(domain=domain, error=str(exc)[:200], checked_at=ts)


# ---------------------------------------------------------------------------
# Check 5: Contact Page Scanner (extended PublicWebConnector logic)
# ---------------------------------------------------------------------------

_CONTACT_SLUGS = ["/contact", "/contact-us", "/about", "/about-us", "/team", "/reach-us"]

# Patterns for address detection (very loose — flag for human review)
_ADDRESS_RE = re.compile(
    r"\b(\d{1,5}[\s,]+[A-Za-z][\w\s,\-\.]{10,80}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Place|Pl|Court|Ct)[\w\s,\-\.]{0,40})\b",
    re.IGNORECASE
)

# Generic phone number pattern (international variants)
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{1,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{4}"
)


def scan_contact_page(base_url: str, rate_limit_seconds: float = 1.5) -> ContactPageResult:
    """
    Scan the company's homepage and common contact/about sub-pages for:
      - Links to /contact, /about, /team pages
      - LinkedIn company page URL
      - Physical address mentions (heuristic)
      - Public email addresses
      - Phone numbers

    Respects rate limiting.  Reads only public HTML.
    """
    ts = _utc_now_str()
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    headers = {
        "User-Agent": "ImpexBuyerVerificationBot/1.0 (+https://github.com/impex-bot)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en",
    }

    contact_links: list[str] = []
    linkedin_url: Optional[str] = None
    detected_addresses: list[str] = []
    detected_emails: list[str] = []
    detected_phones: list[str] = []
    last_error: Optional[str] = None

    # Pages to check: homepage + first matching contact slug
    pages_to_check = [base_url]

    try:
        # First: fetch homepage to find contact links
        time.sleep(rate_limit_seconds)
        resp = httpx.get(base_url, headers=headers, timeout=10.0, follow_redirects=True)
        body = resp.text[:30000]

        # Find internal contact-style links
        all_hrefs = re.findall(r'href=["\']([^"\']{1,200})["\']', body, re.IGNORECASE)
        for href in all_hrefs:
            href_lower = href.lower()
            for slug in _CONTACT_SLUGS:
                if slug in href_lower and href not in contact_links:
                    # Build absolute URL
                    if href.startswith("http"):
                        contact_links.append(href)
                    elif href.startswith("/"):
                        from urllib.parse import urlparse
                        parsed = urlparse(base_url)
                        contact_links.append(f"{parsed.scheme}://{parsed.netloc}{href}")
                    break

        # Find LinkedIn company URL
        li_match = re.search(
            r'https?://(?:www\.)?linkedin\.com/company/[A-Za-z0-9\-_%]+',
            body, re.IGNORECASE
        )
        if li_match:
            linkedin_url = li_match.group(0)

        # Add one contact page to scan queue
        if contact_links:
            pages_to_check.append(contact_links[0])

    except Exception as exc:
        last_error = str(exc)[:200]

    # Scan all pages for emails, phones, addresses
    for page_url in pages_to_check:
        try:
            if page_url != base_url:
                time.sleep(rate_limit_seconds)
            resp = httpx.get(page_url, headers=headers, timeout=10.0, follow_redirects=True)
            body = resp.text[:30000]

            # Emails
            raw_emails = re.findall(
                r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
                body
            )
            for e in raw_emails:
                if (
                    not e.endswith((".png", ".jpg", ".gif", ".svg", ".css", ".js"))
                    and "example" not in e
                    and "noreply" not in e.lower()
                    and e not in detected_emails
                ):
                    detected_emails.append(e)

            # Phone numbers
            for m in _PHONE_RE.finditer(body):
                candidate = m.group(0).strip()
                if len(re.sub(r"\D", "", candidate)) >= 7 and candidate not in detected_phones:
                    detected_phones.append(candidate)

            # Addresses (heuristic — label as inferred)
            for m in _ADDRESS_RE.finditer(body):
                addr = m.group(0).strip()
                if addr not in detected_addresses:
                    detected_addresses.append(addr)

        except Exception as exc:
            last_error = str(exc)[:200]

    return ContactPageResult(
        base_url=base_url,
        contact_links=contact_links[:5],
        linkedin_url=linkedin_url,
        detected_addresses=detected_addresses[:3],
        detected_emails=list(set(detected_emails))[:5],
        detected_phones=list(set(detected_phones))[:5],
        error=last_error,
        checked_at=ts,
    )


# ---------------------------------------------------------------------------
# Master Enrichment Function
# ---------------------------------------------------------------------------

def enrich_domain(
    domain_or_url: str,
    run_smtp: bool = True,
    run_whois: bool = True,
    run_contact: bool = True,
    rate_limit_seconds: float = 1.5,
) -> DomainEnrichmentResult:
    """
    Run all technical domain checks and compute score deltas.

    Args:
        domain_or_url: bare domain, URL, or email address.
        run_smtp:      attempt SMTP EHLO probe (may be blocked on cloud networks).
        run_whois:     run WHOIS lookup.
        run_contact:   scan company contact page.
        rate_limit_seconds: minimum gap between HTTP requests.

    Returns:
        DomainEnrichmentResult with per-check results and score deltas.

    PRD Rule: score deltas must be evidence-based.  No score boost without
    a concrete positive signal. Absence of a signal is neutral (not negative)
    unless it confirms a specific fraud pattern.
    """
    domain = _extract_domain(domain_or_url)
    result = DomainEnrichmentResult(domain=domain)

    email_delta = 0.0
    website_delta = 0.0
    independent_delta = 0.0
    flags: list[str] = []
    notes: list[str] = []

    # ── 1. DNS MX ─────────────────────────────────────────────────────────
    mx = check_dns_mx(domain)
    result.mx = mx

    if mx.has_mx:
        email_delta += 5.0   # Mail infrastructure confirmed
        notes.append(f"MX confirmed: {', '.join(mx.records[:2])}")
    elif mx.error and "NXDOMAIN" in mx.error:
        email_delta -= 5.0   # Domain doesn't exist — serious negative
        flags.append("FLAG_DOMAIN_NOT_FOUND")
        notes.append("MX NXDOMAIN: domain not registered in DNS")
    else:
        notes.append(f"No MX records: {mx.error or 'none found'}")

    # ── 2. SMTP Probe ─────────────────────────────────────────────────────
    if run_smtp and mx.has_mx and mx.records:
        primary_mx = sorted(zip(mx.priority, mx.records))[0][1]
        smtp = probe_smtp(primary_mx)
        result.smtp = smtp

        if smtp.reachable:
            email_delta += 3.0
            notes.append(f"SMTP handshake succeeded: {primary_mx}")
        else:
            notes.append(f"SMTP unreachable ({smtp.error}) — inconclusive (port 25 often blocked)")

    # ── 3. TLS Certificate ────────────────────────────────────────────────
    tls = check_tls(domain)
    result.tls = tls

    if tls.valid:
        if tls.days_to_expiry is not None and tls.days_to_expiry > 30:
            website_delta += 3.0
            notes.append(f"TLS valid, expires in {tls.days_to_expiry} days (issuer: {tls.issuer})")
        elif tls.days_to_expiry is not None and tls.days_to_expiry <= 30:
            flags.append("FLAG_TLS_EXPIRING_SOON")
            notes.append(f"TLS valid but expires in {tls.days_to_expiry} days — renewal overdue")
        else:
            website_delta += 2.0
            notes.append(f"TLS valid (expiry unknown)")
    else:
        flags.append("FLAG_TLS_INVALID")
        notes.append(f"TLS invalid: {tls.error}")

    # ── 4. WHOIS Age ──────────────────────────────────────────────────────
    if run_whois:
        w = check_whois_age(domain)
        result.whois = w

        if w.domain_age_days is not None:
            if w.domain_age_days < 90:
                flags.append("FLAG_DOMAIN_AGE_UNDER_90_DAYS")
                notes.append(
                    f"Domain only {w.domain_age_days} days old — potential fraud risk. "
                    f"Requires human review."
                )
            elif w.domain_age_days >= 365:
                independent_delta += 3.0
                notes.append(f"Domain age {w.domain_age_days} days — established presence.")
            else:
                notes.append(f"Domain age {w.domain_age_days} days — within normal range.")
        else:
            notes.append(f"WHOIS age unavailable: {w.error or 'no creation date'}")

    # ── 5. Contact Page ───────────────────────────────────────────────────
    if run_contact:
        # Reconstruct a base URL
        contact = scan_contact_page(f"https://{domain}", rate_limit_seconds)
        result.contact_page = contact

        if contact.linkedin_url:
            independent_delta += 2.0
            notes.append(f"LinkedIn company page found: {contact.linkedin_url}")

        if contact.detected_emails:
            # Additional public email addresses discovered — do NOT overwrite lead email,
            # just note them as evidence
            independent_delta += 1.0
            notes.append(
                f"Public contact emails found on website: "
                f"{', '.join(contact.detected_emails[:2])}"
            )

        if contact.detected_addresses:
            independent_delta += 1.0
            notes.append(
                f"Physical address hint found on website "
                f"(inferred — not confirmed): {contact.detected_addresses[0][:80]}"
            )

        if contact.error:
            notes.append(f"Contact page scan partial error: {contact.error}")

    # ── Clamp deltas ──────────────────────────────────────────────────────
    result.email_score_delta = max(-15.0, min(email_delta, 15.0))
    result.website_score_delta = max(-15.0, min(website_delta, 15.0))
    result.independent_score_delta = max(-15.0, min(independent_delta, 15.0))
    result.new_flags = flags
    result.evidence_notes = notes

    return result

