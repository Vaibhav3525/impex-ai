# Data Sources & Discovery Engine Register

## Objective
Establish a transparent, legally compliant data ingestion framework for identifying international buyers for Indian exporters, without violating platform terms, engaging in unauthorized scraping, or purchasing unverified data.

---

## Source Matrix & Access Methodology

### 1. Government and Official Trade Promotion Organizations

| Source Name | Portal URL | Type of Data | Legal Access Method | Cost | Limitations & Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DGFT (Directorate General of Foreign Trade)** | https://www.dgft.gov.in/ | Trade notices, IEC registries, trade policy circulars | Public search & authorized APIs | Free | Excellent for verifying Indian exporter credentials and official trade notifications. |
| **APEDA (Agri & Processed Food Export Dev Authority)** | https://apeda.gov.in/ | Agri-product buyer directories, trade fairs, international buyer-seller meets | Published buyer lists & official trade directories | Free | Highly authoritative for agricultural and food commodities. Requires periodic catalog refresh. |
| **Indian Trade Portal** | https://www.indiantradeportal.in/ | HS code tariff data, importing country standards, trade leads | Public portal queries | Free | Authoritative source for preferential tariff rules, SPS/TBT requirements, and trade contact points. |
| **Ministry of External Affairs & Embassies** | https://www.mea.gov.in/ | Commercial reports, bilateral trade directories, verified local importers | Official embassy commercial wing bulletins | Free | High trust factor. Official diplomatic trade leads are pre-vetted for legitimacy. |
| **UN Comtrade** | https://comtradeplus.un.org/ | Bilateral trade statistics by HS code and country | Official UN Comtrade v1 REST API | Free tier (Subscription key available) | **CRITICAL RULE**: Macro trade data indicates market demand by country, NOT individual buyer credentials. Used strictly for country market scoring. |

---

### 2. B2B Marketplaces & Commercial Portals

| Marketplace | Stated Terms & Access Strategy | Integration Plan | Operating Cost |
| :--- | :--- | :--- | :--- |
| **IndiaMART** | Strict anti-scraping policy. Authorized CRM API available for verified sellers with paid accounts. | Integrate via IndiaMART Lead Manager API webhook using registered seller credentials. | Included with paid IndiaMART seller tiers. |
| **Alibaba.com** | Anti-bot mechanisms (Akamai/Cloudflare). Scraping strictly prohibited. Authorized Open Platform API available. | Standard API access or authorized RFQ buyer inquiry exports. | Free/Partner tier. |
| **Global Sources** | Public supplier/buyer directory with terms prohibiting bulk automated harvesting. | Manual search & lawful CSV export of verified buyer inquiries. | Standard account tier. |
| **TradeKey** | Public trade leads and supplier inquiries. | RSS feeds and public buyer inquiry forms. | Free / Basic tier. |

---

### 3. Corporate Websites & Authoritative Business Registries

| Source Category | Methodology | Verification Value |
| :--- | :--- | :--- |
| **National Corporate Registries** (e.g. UK Companies House, US OpenCorporates, EU VIES, ACRA Singapore) | Official open data APIs and public company search. | Confirms legal existence, active trading status, registered address, and filing compliance (20 pts). |
| **Company Official Websites** | Direct HTTP status probe, TLS certificate inspection, domain age calculation, and public `/contact` or `/about` discovery. | Confirms active digital presence and consistent contact details (15 pts). |
| **Domain DNS & MX Servers** | DNS lookup for MX records (`dnspython`), SPF, DKIM, and SMTP greeting handshake. | Proves business email deliverability and avoids sending to non-existent or temporary mailboxes (15 pts). |

---

## Standard Ingested Record Schema (20 Mandatory Fields)

Every raw record ingested into the system is normalized into the following standard structure:

```json
{
  "lead_id": "LID-2026-0001",
  "company_name": "Nordic Food Imports AS",
  "country": "Norway",
  "city": "Oslo",
  "website": "https://www.nordicfoodimports.no",
  "product_category": "Basmati Rice & Spices",
  "contact_name": "Erik Solberg",
  "job_title": "Procurement Director",
  "business_email": "erik.solberg@nordicfoodimports.no",
  "phone_number": "+47 22 12 34 56",
  "source": "APEDA International Buyer Directory",
  "source_url": "https://apeda.gov.in/buyer-directory/norway-food-importers.pdf",
  "import_evidence": "Listed as registered importer of grain products under Norway Food Safety Authority",
  "verification_status": "Verified",
  "buyer_score": 88,
  "risk_flags": [],
  "last_verified": "2026-10-28T12:00:00Z",
  "outreach_status": "Not Contacted",
  "next_followup": null,
  "notes": "Verified corporate registration against Brønnøysundregistrene (Org nr: 987654321)."
}
```

