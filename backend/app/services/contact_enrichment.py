"""Read published company contact details and retain the exact page provenance."""
import re
import time
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import unquote, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.services.public_source_discovery import DIRECTORIES

USER_AGENT = "ImpExAI-PublicContactBot"
EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
CONTACT_PATH = re.compile(r"contact|kontakt|impressum|about-us", re.I)
LABELED_PHONE = re.compile(r"(?:telephone|telefon|phone|tel\.?|T)\s*[:.]\s*(\+?[\d(][\d\s().\-]{6,35})", re.I)
ROLE_EMAIL = re.compile(r"^(info|contact|sales|enquir\w*|office|hello|trade|import\w*|purchas\w*|sourc\w*|procure\w*)$", re.I)


def _host(url):
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def _validate_url(url, company_host):
    parsed = urlsplit(url)
    if parsed.scheme not in {"https", "http"} or parsed.username or parsed.password:
        raise ValueError("Unsupported company URL")
    if parsed.port not in {None, 80, 443} or _host(url) != company_host:
        raise ValueError("Page leaves the listed company website")
    answers = [row[4][0] for row in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)]
    if not answers or any(not ipaddress.ip_address(address).is_global for address in answers):
        raise ValueError("Company URL requires public internet addresses")


def _get(client, url, company_host, deadline):
    for _ in range(4):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError("Company scan time limit reached")
        _validate_url(url, company_host)
        with client.stream("GET", url, timeout=min(4, remaining)) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes(chunk_size=16_384):
                if time.monotonic() > deadline or len(body) + len(chunk) > 1_000_000:
                    raise ValueError("Company page exceeded scan limits")
                body.extend(chunk)
            return url, response.headers.get("content-type", ""), bytes(body)
    raise ValueError("Too many company page redirects")


def extract_contacts(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("script,style,noscript,svg"):
        tag.decompose()
    candidates = []
    for link in soup.select("a[href]"):
        href = unquote(link["href"])
        if href.lower().startswith("mailto:"):
            candidates.extend(("email", match.group()) for match in EMAIL.finditer(href.split("?", 1)[0]))
        elif href.lower().startswith("tel:"):
            number = href[4:].split("?", 1)[0].strip()
            if 7 <= len(re.sub(r"\D", "", number)) <= 15:
                candidates.append(("phone", number))
    candidates.extend(("email", match.group()) for match in EMAIL.finditer(soup.get_text(" ", strip=True)))
    text = soup.get_text(" ", strip=True)
    for match in LABELED_PHONE.finditer(text):
        number = match.group(1).strip()
        if 7 <= len(re.sub(r"\D", "", number)) <= 15:
            candidates.append(("phone", number))
    contacts = []
    seen = set()
    for kind, value in candidates:
        value = value.lower() if kind == "email" else value
        if len(value) > 255 or (kind, value) in seen:
            continue
        if kind == "email":
            local, domain = value.split("@")
            if domain in {"example.com", "example.org", "sentry.io"} or any(
                word in local for word in ("noreply", "no-reply", "privacy", "abuse", "webmaster")
            ):
                continue
        seen.add((kind, value))
        contacts.append({"type": kind, "value": value, "source_url": page_url})
    links = []
    for link in soup.select("a[href]"):
        url = urljoin(page_url, link["href"]).split("#", 1)[0]
        if _host(url) == _host(page_url) and CONTACT_PATH.search(urlsplit(url).path) and url not in links:
            links.append(url)
    return contacts, links[:3]


def scan_company(website):
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "status": "No published contacts found",
              "contacts": [], "pages": [], "errors": []}
    if not website:
        result["status"] = "Company website needed"
        return result
    if not website.startswith(("http://", "https://")):
        website = "https://" + website
    company_host = _host(website)
    deadline = time.monotonic() + 18
    seen = set()
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=False, trust_env=False) as client:
        try:
            parsed = urlsplit(website)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            try:
                _, _, robots_body = _get(client, robots_url, company_host, deadline)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {404, 410}:
                    raise
                robots_body = b""
            rules = RobotFileParser()
            rules.parse(robots_body.decode("utf-8", errors="replace").splitlines())
            pending = [website]
            while pending and len(result["pages"]) < 4:
                url = pending.pop(0)
                if url in seen:
                    continue
                if not rules.can_fetch(USER_AGENT, url):
                    result["errors"].append("RobotsExcluded")
                    continue
                seen.add(url)
                try:
                    final_url, content_type, body = _get(client, url, company_host, deadline)
                    if not rules.can_fetch(USER_AGENT, final_url):
                        continue
                    if "text/html" not in content_type.lower():
                        continue
                    result["pages"].append(final_url)
                    contacts, links = extract_contacts(body, final_url)
                    result["contacts"].extend(contacts)
                    pending.extend(link for link in links if link not in seen)
                except (httpx.HTTPError, ValueError, OSError) as exc:
                    result["errors"].append(type(exc).__name__)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            result["errors"].append(type(exc).__name__)
    unique = {(c["type"], c["value"]): c for c in result["contacts"]}
    result["contacts"] = list(unique.values())[:30]
    if result["contacts"]:
        result["status"] = "Published contacts found"
    elif result["errors"]:
        result["status"] = "Website scan incomplete"
    return result


def enrich_contact_batch(db: Session, limit=4):
    names = [source.name for source in DIRECTORIES]
    leads = db.query(Lead).filter(Lead.source.in_(names)).order_by(Lead.id).all()
    pending = [lead for lead in leads if not lead.contact_enrichment]
    selected = pending[:limit]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(scan_company, [lead.website for lead in selected]))
    updated = with_contacts = 0
    for lead, result in zip(selected, results):
        db.refresh(lead)
        emails = [c["value"] for c in result["contacts"] if c["type"] == "email"
                  and ROLE_EMAIL.match(c["value"].split("@")[0])
                  and _host("https://" + c["value"].split("@")[1]) == _host(lead.website or "")]
        phones = [c["value"] for c in result["contacts"] if c["type"] == "phone"]
        changed = False
        if not lead.business_email and emails:
            lead.business_email = emails[0]
            changed = True
        if not lead.phone_number and phones:
            lead.phone_number = phones[0]
            changed = True
        lead.contact_enrichment = result
        updated += int(changed)
        with_contacts += int(bool(result["contacts"]))
    db.commit()
    return {"processed": len(selected), "updated": updated, "with_contacts": with_contacts,
            "remaining": max(0, len(pending) - len(selected)),
            "results": [{"lead_id": lead.lead_id, "company_name": lead.company_name, "status": result["status"]}
                        for lead, result in zip(selected, results)]}
