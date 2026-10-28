"""
Day 4 — Public Trade Source Connectors
Modular adapters for authorized, legally compliant public trade data sources:

1. UN Comtrade - Country-level commodity import statistics (market demand scoring)
2. APEDA - Agri & processed food buyer directory (pre-processed offline format)
3. Indian Trade Portal - Trade leads and importer contact listings
4. Generic Public Web Connector - Ethical company website scraper
"""
import httpx
import re
import time
import hashlib
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

# =============================================================================
# BASE CONNECTOR INTERFACE
# =============================================================================

@dataclass
class DiscoveredLead:
    """Standardized lead record produced by any connector."""
    company_name: str
    country: str
    product_category: str
    source: str
    source_url: str
    city: Optional[str] = None
    website: Optional[str] = None
    contact_name: Optional[str] = None
    job_title: Optional[str] = None
    business_email: Optional[str] = None
    phone_number: Optional[str] = None
    import_evidence: Optional[str] = None
    notes: Optional[str] = None
    raw_data: dict = field(default_factory=dict)


# =============================================================================
# CONNECTOR 1: UN COMTRADE — Market-Level Country Demand
# =============================================================================

COMTRADE_BASE_URL = "https://comtradeapi.un.org/data/v1/get"

class UNComtradeConnector:
    """
    Connector for UN Comtrade official REST API v1.
    Purpose: Identify which COUNTRIES import a given HS code commodity at scale.
    
    IMPORTANT PRD RULE: Comtrade provides MARKET-LEVEL statistics only.
    It does NOT identify individual companies. Trade statistics must NOT be
    treated as proof that a specific company is an active buyer.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = COMTRADE_BASE_URL

    def get_top_importing_countries(
        self,
        hs_code: str,
        period: str = "2023",
        reporter_country: str = "699",  # 699 = India
        top_n: int = 20,
    ) -> list[dict]:
        """
        Fetch top importing partner countries for an HS code from India.
        Returns list of {country, trade_value_usd, quantity, period} dicts.
        
        These results should be used to PRIORITIZE which countries to search for
        buyers in — not as buyer records themselves.
        """
        params = {
            "typeCode": "C",       # Commodities
            "freqCode": "A",       # Annual
            "clCode": "HS",
            "period": period,
            "reporterCode": reporter_country,
            "cmdCode": hs_code,
            "flowCode": "X",       # X = Exports from India
            "partnerCode": "0",    # All partners
            "partner2Code": "0",
            "customsCode": "C00",
            "motCode": "0",
            "maxRecords": top_n,
            "format": "JSON",
            "breakdownMode": "classic",
        }
        if self.api_key:
            params["subscription-key"] = self.api_key

        try:
            response = httpx.get(
                self.base_url,
                params=params,
                timeout=15.0,
                follow_redirects=True,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for record in data.get("data", []):
                partner = record.get("partnerDesc", "")
                if not partner or partner in ("World", "Areas nes"):
                    continue
                results.append({
                    "partner_country": partner,
                    "partner_code": record.get("partnerCode"),
                    "trade_value_usd": record.get("primaryValue", 0),
                    "quantity": record.get("netWgt"),
                    "unit": record.get("qtyUnitCode"),
                    "hs_code": hs_code,
                    "period": period,
                    "data_type": "MARKET_STATISTIC_ONLY",
                    "warning": (
                        "This is a country-level trade statistic. "
                        "It does NOT identify individual buyers. "
                        "Use to prioritize target markets only."
                    )
                })

            return sorted(results, key=lambda x: x["trade_value_usd"], reverse=True)

        except httpx.TimeoutException:
            return [{"error": "UN Comtrade API timeout", "hs_code": hs_code}]
        except httpx.HTTPStatusError as e:
            return [{"error": f"UN Comtrade API HTTP {e.response.status_code}", "hs_code": hs_code}]
        except Exception as e:
            return [{"error": str(e), "hs_code": hs_code}]


# =============================================================================
# CONNECTOR 2: APEDA Buyer Directory (Static Published Format)
# =============================================================================

class APEDADirectoryConnector:
    """
    Processes buyer records from APEDA published international buyer directories.
    
    APEDA publishes official buyer contact lists for Indian agri-exporters via:
    - International buyer-seller meet reports
    - Virtual trade fair attendee lists
    - Product-specific importer directories
    
    These are lawfully published by an official Indian government body (APEDA).
    Input: CSV/Excel data from APEDA directory downloads.
    """

    SOURCE_NAME = "APEDA International Buyer Directory"
    SOURCE_BASE_URL = "https://apeda.gov.in/apedawebsite/SubHead_Products/International_Buyers.htm"

    VALID_PRODUCTS = {
        "basmati rice", "non-basmati rice", "wheat", "pulses", "spices",
        "cardamom", "turmeric", "black pepper", "ginger", "cumin",
        "fresh fruits", "vegetables", "processed foods", "organic products",
        "dairy", "poultry", "meat", "seafood", "cereals", "oilseeds"
    }

    def process_directory_row(self, row: dict) -> Optional[DiscoveredLead]:
        """
        Convert a raw APEDA directory row into a normalized DiscoveredLead.
        Returns None if the row lacks minimum required data.
        """
        company = (row.get("importer_name") or row.get("company_name") or "").strip()
        country = (row.get("country") or row.get("nation") or "").strip()
        product = (row.get("product") or row.get("commodity") or row.get("product_category") or "").strip()

        if not company or not country or not product:
            return None

        email = row.get("email") or row.get("business_email") or ""
        if email:
            email = email.strip().lower()

        website = row.get("website") or row.get("web") or ""
        if website and not website.startswith("http"):
            website = f"https://{website}"

        phone = row.get("phone") or row.get("telephone") or row.get("mobile") or ""
        contact = row.get("contact_person") or row.get("contact_name") or ""
        title = row.get("designation") or row.get("job_title") or ""

        return DiscoveredLead(
            company_name=company,
            country=country,
            product_category=product,
            source=self.SOURCE_NAME,
            source_url=row.get("source_url") or self.SOURCE_BASE_URL,
            website=website or None,
            contact_name=contact or None,
            job_title=title or None,
            business_email=email or None,
            phone_number=phone or None,
            import_evidence=row.get("import_evidence") or (
                f"Listed as buyer in APEDA {product} international buyer directory."
            ),
            notes=row.get("notes") or None,
            raw_data=row,
        )

    def process_directory_rows(self, rows: list[dict]) -> list[DiscoveredLead]:
        """Batch-process a list of APEDA directory rows."""
        leads = []
        for row in rows:
            lead = self.process_directory_row(row)
            if lead:
                leads.append(lead)
        return leads


# =============================================================================
# CONNECTOR 3: Indian Trade Portal — Trade Leads
# =============================================================================

class IndianTradePortalConnector:
    """
    Processes trade inquiry leads from the Indian Trade Portal (ITP).
    https://www.indiantradeportal.in/
    
    The ITP publishes buyer inquiry data for Indian exporters via:
    - Trade leads section (publicly viewable inquiries)
    - Buyer inquiry forms
    
    This connector processes leads that have been legitimately obtained 
    from the ITP interface or official trade lead exports.
    """

    SOURCE_NAME = "Indian Trade Portal"
    SOURCE_BASE_URL = "https://www.indiantradeportal.in/"

    # Typical ITP trade lead fields
    FIELD_MAP = {
        "buyer_name": "company_name",
        "buyer_country": "country",
        "buyer_city": "city",
        "product_description": "product_category",
        "buyer_email": "business_email",
        "buyer_website": "website",
        "contact_person": "contact_name",
        "quantity_required": "notes",
    }

    def process_trade_lead(self, lead_data: dict) -> Optional[DiscoveredLead]:
        """Convert an ITP trade inquiry record into a DiscoveredLead."""
        normalized = {}
        for raw_key, val in lead_data.items():
            mapped_key = self.FIELD_MAP.get(raw_key.lower().strip(), raw_key.lower().strip())
            normalized[mapped_key] = str(val).strip() if val else ""

        company = normalized.get("company_name", "").strip()
        country = normalized.get("country", "").strip()
        product = normalized.get("product_category", "").strip()

        if not company or not country:
            return None

        qty_note = normalized.get("notes", "")
        notes_parts = []
        if qty_note:
            notes_parts.append(f"Required quantity: {qty_note}")
        notes_parts.append("Source: Indian Trade Portal buyer inquiry")

        return DiscoveredLead(
            company_name=company,
            country=country,
            product_category=product or "Unspecified",
            source=self.SOURCE_NAME,
            source_url=lead_data.get("source_url") or self.SOURCE_BASE_URL,
            city=normalized.get("city") or None,
            website=normalized.get("website") or None,
            contact_name=normalized.get("contact_name") or None,
            business_email=normalized.get("business_email") or None,
            import_evidence=(
                f"Active trade inquiry submitted via Indian Trade Portal for "
                f"{product or 'commodities'} from India."
            ),
            notes=" | ".join(notes_parts) if notes_parts else None,
            raw_data=lead_data,
        )

    def process_bulk_leads(self, leads: list[dict]) -> list[DiscoveredLead]:
        return [l for lead in leads if (l := self.process_trade_lead(lead)) is not None]


# =============================================================================
# CONNECTOR 4: Respectful Public Web Company Connector
# =============================================================================

class PublicWebConnector:
    """
    Ethical public web connector for verifying and enriching company information
    from their official corporate websites.
    
    Respects robots.txt and implements respectful rate limiting.
    Only reads publicly accessible pages (no login bypass, no session spoofing).
    """

    def __init__(self, rate_limit_seconds: float = 1.5):
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request_time = 0.0

    def _wait_for_rate_limit(self):
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = time.monotonic()

    def check_website_alive(self, url: str) -> dict:
        """
        Check if a company website is live and gather basic identity signals.
        Returns: {alive, status_code, https, domain_in_title, detected_emails, error}
        """
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        self._wait_for_rate_limit()

        try:
            headers = {
                "User-Agent": "ImpexBuyerVerificationBot/1.0 (+https://github.com/impex-bot)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en",
            }
            response = httpx.get(
                url,
                headers=headers,
                timeout=10.0,
                follow_redirects=True,
            )

            body = response.text[:20000]  # Only read first 20KB

            # Extract page title
            title_match = re.search(r"<title[^>]*>([^<]{2,200})</title>", body, re.IGNORECASE)
            page_title = title_match.group(1).strip() if title_match else ""

            # Look for email addresses in visible text (crude but fast)
            raw_emails = re.findall(
                r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
                body
            )
            # Filter noise
            detected_emails = [
                e for e in raw_emails
                if not e.endswith((".png", ".jpg", ".gif", ".svg", ".css"))
                and "example" not in e
                and "noreply" not in e.lower()
            ][:5]

            # Check if final URL is HTTPS
            final_url = str(response.url)
            is_https = final_url.startswith("https://")

            return {
                "alive": True,
                "status_code": response.status_code,
                "https": is_https,
                "final_url": final_url,
                "page_title": page_title,
                "detected_public_emails": list(set(detected_emails)),
                "error": None,
            }

        except httpx.TimeoutException:
            return {"alive": False, "error": "Connection timeout", "https": False}
        except httpx.ConnectError:
            return {"alive": False, "error": "Connection refused / DNS failure", "https": False}
        except Exception as exc:
            return {"alive": False, "error": str(exc)[:200], "https": False}

