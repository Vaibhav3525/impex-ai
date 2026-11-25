"""Discover prospective buyers from public trade association directories."""
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.product_profile import ProductProfile
from app.schemas.lead import LeadCreate
from app.services.lead_service import generate_dedup_hash, ingest_lead


USER_AGENT = "ImpExAI-PublicDirectoryBot"
MAX_PAGE_BYTES = 1_500_000


@dataclass(frozen=True)
class Directory:
    name: str
    url: str
    product_keyword: str
    countries: tuple[str, ...]
    parser: str


DIRECTORIES = (
    Directory(
        "The Rice Association", "https://www.riceassociation.org.uk/ra-members",
        "rice", ("United Kingdom",), "rice",
    ),
    Directory(
        "UK Tea & Infusions Association", "https://tea.co.uk/tea-directory/uktia-members",
        "tea", ("United Kingdom",), "tea",
    ),
    Directory(
        "European Spice Association", "https://www.esa-spices.org/index.php/members/list-of-members",
        "spice", ("Germany", "United Kingdom", "Netherlands"), "spice",
    ),
)


def _fetch(client: httpx.Client, url: str, expected_type: str) -> bytes:
    with client.stream("GET", url) as response:
        response.raise_for_status()
        if response.headers.get("content-type", "").split(";")[0].strip().lower() != expected_type:
            raise ValueError("Unexpected directory response type")
        body = bytearray()
        for chunk in response.iter_bytes(chunk_size=16_384):
            if len(body) + len(chunk) > MAX_PAGE_BYTES:
                raise ValueError("Directory page exceeded the size limit")
            body.extend(chunk)
        return bytes(body)


def _fetch_directory(client: httpx.Client, source: Directory) -> bytes:
    # Only source constants are fetched. Listed company links are stored, never fetched.
    parsed = urlsplit(source.url)
    try:
        robots = _fetch(client, f"https://{parsed.netloc}/robots.txt", "text/plain")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code not in {404, 410}:
            raise
    else:
        rules = RobotFileParser()
        rules.parse(robots.decode("utf-8", errors="replace").splitlines())
        if not rules.can_fetch(USER_AGENT, source.url):
            raise ValueError("Directory excludes automated requests")
    return _fetch(client, source.url, "text/html")


def _website(value: str) -> str | None:
    try:
        url = urlsplit(value)
        host = (url.hostname or "").removeprefix("www.")
        if url.scheme not in {"http", "https"} or not host or url.username or url.password:
            return None
        if url.port not in {None, 80, 443} or host in {"tea.co.uk", "riceassociation.org.uk"}:
            return None
        if host in {"linkedin.com", "facebook.com", "instagram.com", "youtube.com"}:
            return None
        if "." in host and not host.startswith(("maps.", "www.google.")):
            return value.split("#", 1)[0]
    except ValueError:
        pass
    return None


def _directory_rows(soup: BeautifulSoup, parser: str):
    if parser == "rice":
        for card in soup.select(".wixui-repeater__item"):
            heading = card.select_one("h1,h2,h3")
            for link in card.select("a[href]"):
                website = _website(link["href"])
                if heading and website and link.get_text(" ", strip=True).casefold() == "visit site":
                    yield heading.get_text(" ", strip=True), website, "Listed in the UK rice trade membership directory.", "United Kingdom"
                    break
    elif parser == "tea":
        for card in soup.select(".indented"):
            website = next((url for a in card.select(".links a[href]") if (url := _website(a["href"]))), None)
            name = next(card.stripped_strings, "")
            if website and name:
                yield name, website, "Listed in the UK tea trade membership directory. Confirm the company's location and product fit.", "United Kingdom"
    else:
        table = soup.find("table")
        if table is None:
            return
        for row in table.select("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td", recursive=False)]
            if len(cells) == 2:
                name, country = cells
                if not any(word in name.casefold() for word in ("association", "verband", "federation", "vereniging", "federatie")):
                    yield name, None, f"Listed as a spice industry member in {country}.", country


def extract_candidates(html: bytes, source: Directory, product_name: str, country: str) -> list[LeadCreate]:
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for name, website, evidence, listed_country in _directory_rows(soup, source.parser):
        if listed_country.casefold() != country.casefold() or not 2 <= len(name) <= 255:
            continue
        candidates.append(LeadCreate(
            company_name=name, country=country, website=website,
            product_category=product_name, source=source.name, source_url=source.url,
            notes=f"{evidence} Review the directory listing and confirm buying activity and exact product fit.",
        ))
    return candidates


def run_public_discovery(db: Session, max_pairs: int = 6, max_leads_per_pair: int = 10) -> dict:
    products = db.query(ProductProfile).filter(ProductProfile.is_active.is_(True)).order_by(ProductProfile.id).all()
    pairs = []
    for product in products:
        markets = {c.strip().casefold() for c in product.target_countries or [] if isinstance(c, str)}
        excluded = {c.strip().casefold() for c in product.excluded_countries or [] if isinstance(c, str)}
        for source in DIRECTORIES:
            if source.product_keyword in product.product_name.casefold():
                pairs.extend((product.product_name, country, source) for country in source.countries
                             if country.casefold() in markets - excluded)
    if not pairs:
        return {"status": "No matching public directories", "pairs_checked": 0, "created": 0, "duplicates": 0, "errors": []}

    start = date.today().toordinal() % len(pairs)
    selected = (pairs[start:] + pairs[:start])[:max_pairs]
    pages = {}
    errors = {}
    created = duplicates = checked = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=7, follow_redirects=False, trust_env=False) as client:
        for product, country, source in selected:
            if source not in pages and source not in errors:
                try:
                    pages[source] = _fetch_directory(client, source)
                except (httpx.HTTPError, ValueError) as exc:
                    errors[source] = f"{source.name}: {type(exc).__name__}"
            if source in errors:
                continue
            checked += 1
            candidates = extract_candidates(pages[source], source, product, country)
            pair_created = 0
            for candidate in candidates:
                if pair_created >= max_leads_per_pair:
                    break
                try:
                    _, is_new = ingest_lead(db, candidate)
                except IntegrityError:
                    db.rollback()
                    key = generate_dedup_hash(candidate.company_name, candidate.country, candidate.website)
                    if not db.query(Lead.id).filter_by(dedup_hash=key).first():
                        raise
                    is_new = False
                created += int(is_new)
                pair_created += int(is_new)
                duplicates += int(not is_new)

    status = "Completed with source errors" if checked and errors else "Sources unavailable" if errors else "Completed"
    return {"status": status, "pairs_checked": checked, "created": created,
            "duplicates": duplicates, "errors": list(errors.values())}
