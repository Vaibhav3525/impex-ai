"""
Day 3 — Batch Lead Ingestion Engine
Handles CSV and JSON bulk uploads with:
- Field validation and normalization
- SHA-256 duplicate rejection
- Per-row error reporting
- Auto-verification on import
"""
import csv
import json
import io
from typing import List, Optional
from dataclasses import dataclass, field


REQUIRED_FIELDS = {"company_name", "country", "source", "product_category"}

FREE_EMAIL_DOMAINS_QUICK = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "protonmail.com", "icloud.com", "mail.com", "tempmail.com", "mailinator.com"
}

# Canonical field aliases: map common CSV header variants → internal field name
FIELD_ALIASES: dict[str, str] = {
    "company": "company_name",
    "firm": "company_name",
    "organization": "company_name",
    "organisation": "company_name",
    "name": "company_name",
    "nation": "country",
    "location": "country",
    "website_url": "website",
    "web": "website",
    "url": "website",
    "homepage": "website",
    "product": "product_category",
    "commodity": "product_category",
    "goods": "product_category",
    "item": "product_category",
    "contact": "contact_name",
    "person": "contact_name",
    "full_name": "contact_name",
    "email": "business_email",
    "email_address": "business_email",
    "mail": "business_email",
    "phone": "phone_number",
    "telephone": "phone_number",
    "mobile": "phone_number",
    "tel": "phone_number",
    "title": "job_title",
    "role": "job_title",
    "position": "job_title",
    "designation": "job_title",
    "city_name": "city",
    "town": "city",
    "origin": "source",
    "data_source": "source",
    "evidence_url": "source_url",
    "source_link": "source_url",
    "import_activity": "import_evidence",
    "purchasing_evidence": "import_evidence",
    "remark": "notes",
    "comment": "notes",
}


@dataclass
class RowResult:
    row_number: int
    status: str  # "created" | "duplicate" | "updated" | "error"
    lead_id: Optional[str] = None
    company_name: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class BatchImportResult:
    source_filename: str
    total_rows: int
    created: int = 0
    duplicates: int = 0
    updated: int = 0
    errors: int = 0
    rows: List[RowResult] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "source": self.source_filename,
            "total_rows": self.total_rows,
            "created": self.created,
            "duplicates_skipped": self.duplicates,
            "updated_with_new_data": self.updated,
            "error_rows": self.errors,
            "error_rate_pct": round((self.errors / max(self.total_rows, 1)) * 100, 1),
        }


def normalize_header(raw: str) -> str:
    """Lower-case, strip, replace spaces with underscores, then apply aliases."""
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    return FIELD_ALIASES.get(key, key)


def validate_row(row: dict, row_num: int) -> tuple[dict, List[str], List[str]]:
    """
    Validates and cleans a single row dict.
    Returns: (cleaned_row, errors, warnings)
    """
    cleaned: dict = {}
    errors: List[str] = []
    warnings: List[str] = []

    # Normalize keys
    for raw_key, val in row.items():
        norm_key = normalize_header(raw_key)
        cleaned[norm_key] = str(val).strip() if val else ""

    # Check required fields
    for req in REQUIRED_FIELDS:
        if not cleaned.get(req):
            errors.append(f"Missing required field: '{req}'")

    # Company name length sanity
    name = cleaned.get("company_name", "")
    if name and len(name) < 3:
        errors.append(f"company_name too short ('{name}')")
    if name and len(name) > 255:
        errors.append("company_name exceeds 255 characters")

    # Country sanity
    country = cleaned.get("country", "")
    if country and len(country) < 2:
        errors.append(f"country value too short ('{country}')")

    # Email hygiene warnings (non-blocking)
    email = cleaned.get("business_email", "")
    if email:
        if "@" not in email:
            errors.append(f"business_email invalid format: '{email}'")
        else:
            domain = email.split("@")[-1].lower()
            if domain in FREE_EMAIL_DOMAINS_QUICK:
                warnings.append(f"Free/personal email domain detected: '@{domain}' — will trigger FLAG_FREE_EMAIL_DOMAIN")

    # Website cleanup
    website = cleaned.get("website", "")
    if website and not website.startswith(("http://", "https://")):
        cleaned["website"] = f"https://{website}"
        warnings.append(f"Auto-prefixed website with https://")

    # Buyer score must not be set externally (security — prevent score injection)
    if "buyer_score" in cleaned:
        del cleaned["buyer_score"]
        warnings.append("External 'buyer_score' was stripped — scores are calculated by the verification engine only")

    return cleaned, errors, warnings


def parse_csv_bytes(content: bytes, encoding: str = "utf-8-sig") -> list[dict]:
    """Parse CSV bytes, returning list of raw row dicts."""
    try:
        text = content.decode(encoding)
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def parse_json_bytes(content: bytes) -> list[dict]:
    """Parse JSON bytes. Accepts a list of objects or a dict with a 'leads' key."""
    data = json.loads(content.decode("utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Allow { "leads": [...] } envelope
        for key in ("leads", "records", "buyers", "data", "results"):
            if key in data and isinstance(data[key], list):
                return data[key]
    raise ValueError("JSON must be a list of objects or a dict with a 'leads' (or 'records') list key")

