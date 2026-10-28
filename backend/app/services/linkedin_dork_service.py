"""
LinkedIn Compliant Persona & Google X-Ray Search Dork Service
PRD §3.D: Lawfully identifies relevant buyer companies and decision-maker roles
(Import Managers, Procurement Directors, Sourcing Managers, Company Owners)
without unauthorized platform scraping, session spoofing, or automated bot bans.
"""

from __future__ import annotations
import urllib.parse
from typing import List, Dict, Any, Optional

TARGET_BUYER_ROLES = [
    "Import Manager",
    "Head of Procurement",
    "Procurement Director",
    "Global Sourcing Manager",
    "Purchasing Director",
    "Commodity Buyer",
    "Managing Director",
    "Supply Chain Director",
    "Category Manager (Food & Beverage)"
]


class LinkedInDorkService:
    """
    Generates compliant search strings and persona templates for identifying
    authorized international buyers.
    """

    def generate_xray_queries(
        self,
        commodity: str,
        country: str,
        roles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Builds Google X-Ray search queries targeting public professional profiles
        lawfully indexed by search engines.
        """
        target_roles = roles or TARGET_BUYER_ROLES[:5]
        role_clause = " OR ".join(f'"{r}"' for r in target_roles)
        commodity_clause = f'"{commodity}"'
        country_clause = f'"{country}"'

        # 1. Decision Maker Profiles (Individuals)
        individual_dork = f'site:linkedin.com/in/ ({role_clause}) AND {commodity_clause} AND {country_clause}'
        individual_url = f"https://www.google.com/search?q={urllib.parse.quote(individual_dork)}"

        # 2. Importer Corporate Pages (Companies)
        company_dork = f'site:linkedin.com/company/ ("Importer" OR "Wholesale Distributor" OR "Food Service") AND {commodity_clause} AND {country_clause}'
        company_url = f"https://www.google.com/search?q={urllib.parse.quote(company_dork)}"

        # 3. Candidate persona templates
        sample_personas = [
            {
                "suggested_role": "Head of Procurement / Sourcing",
                "focus_area": f"Direct procurement of {commodity} shipments",
                "sample_query": individual_dork,
                "google_search_url": individual_url,
                "compliance_note": "Public search engine query. Complies with PRD §3.D (Zero unauthorized scraping)."
            },
            {
                "suggested_role": "Corporate Importer Directory",
                "focus_area": f"Trading companies with active import licenses in {country}",
                "sample_query": company_dork,
                "google_search_url": company_url,
                "compliance_note": "Direct public company discovery without automated account interactions."
            }
        ]

        return {
            "commodity": commodity,
            "country": country,
            "individual_xray_query": individual_dork,
            "individual_search_url": individual_url,
            "company_xray_query": company_dork,
            "company_search_url": company_url,
            "sample_personas": sample_personas,
            "compliance_status": "100% PRD §3.D Compliant (Authorized Open Search Engine Queries)"
        }
