# ImpEx AI — Comprehensive Project Handover & Engineering Specification

> **Project Name:** ImpEx AI (Global Import-Export Buyer Acquisition & Automation Engine)  
> **Repository:** [Vaibhav3525/impex-ai](https://github.com/Vaibhav3525/impex-ai) (Branch: `master`)  
> **Live Production Application:** [https://impex-ai.onrender.com/](https://impex-ai.onrender.com/)  
> **Live API Health Check:** [https://impex-ai.onrender.com/api/v1/health](https://impex-ai.onrender.com/api/v1/health)  
> **Live OpenAPI / Swagger Docs:** [https://impex-ai.onrender.com/docs](https://impex-ai.onrender.com/docs)  
> **Workspace Path:** `d:\antigravity`  
> **Status:** Fully functional, containerized, deployed live on Render free tier, with 138/138 passing unit/integration tests.

---

## 1. Executive Summary & Value Proposition

**ImpEx AI** is a purpose-built B2B trade intelligence, buyer acquisition, and export workflow automation platform tailored for Indian exporters and merchant trade houses.

The platform addresses the highest friction points in cross-border trade:
1. **Zero Data Fabrication Standard:** Replaces unverified lead databases with authentic, provenance-tracked international buyers sourced from verified public directories (APEDA, Dubai Chamber of Commerce, Indo-German Chamber, MEA Indian Embassy Commercial Wings, European Spice Association, Customs registries).
2. **100-Point Algorithmic Verification Engine:** Audits buyer corporate identity, domain DNS MX records, TLS certificates, import evidence, and email syntax before any outreach occurs.
3. **5-Factor Product Matching Engine:** Scores buyer profiles against specific Indian export commodities (HS codes, target countries, exclusion zones, MOQ, payment preferences) with itemized mathematical breakdowns.
4. **15-Stage Export CRM & Financial Pipeline:** Tracks leads from initial discovery through quotation preparation, DGFT-compliant Proforma Invoices, LC negotiations, to confirmed order realization.
5. **Payment Risk Guardian:** Strictly isolates buyer qualification from financial risk. Flags or blocks unsecured payment structures (Open Account, DA 60/90) while approving safe terms (Advance Wire, Irrevocable LC at Sight).
6. **Mode A Assisted Outreach & Cadence:** Implements human-in-the-loop review. Outreach emails are grounded in verified data, placed in a queue for manual approval, and scheduled across a 3-touch cadence (Days 1, 4, 8) with instant auto-halting upon buyer reply.
7. **11-Class Buyer Reply Intelligence:** Classifies incoming inquiries, extracts commercial entities (product, quantity, target price, delivery port, payment method), and automatically advances deal stages.

---

## 2. System Architecture & Tech Stack

```mermaid
flowchart TD
    subgraph Frontend["Frontend Layer (Next.js 14 App Router)"]
        UI["Tailwind CSS + Lucide React Dashboard"]
        Client["api.ts (Auto-detects /api/v1 or local:8000)"]
        UI --> Client
    end

    subgraph Backend["Backend Layer (FastAPI + Python 3.11/3.12)"]
        FastAPIApp["app.main:app (Mounted on /api/v1)"]
        StaticServe["StaticFiles('/app/frontend/out') at /"]
        
        Routers["API Routers:
        - /leads (100-Point Audit & Risk)
        - /products (5-Factor Matching)
        - /pipeline & /deals (15-Stage CRM)
        - /outreach (Mode A Assisted Queue)
        - /replies (11-Class Classifier)
        - /discover (Comtrade, APEDA, Domain)
        - /analytics (KPI Dashboard & CSV)"]
        
        Engines["Business Engines:
        - VerificationService (100-pt rubric)
        - QualificationService (5-factor score)
        - PaymentRiskService (Incoterm/LC audit)
        - EmailComposer & FollowupService
        - ProformaService (Customs PI)
        - ReplyClassifier (NLP/Intent extraction)"]
        
        FastAPIApp --> Routers
        Routers --> Engines
    end

    subgraph Storage["Persistence & External Services"]
        SQLiteDB[("SQLite: impex_leads.db
        (PostgreSQL / Supabase Ready)")]
        SMTP["Hostinger SMTP / SSL:465"]
        GeminiAPI["Google Gemini 1.5 Pro / Flash"]
    end

    Client -->|HTTP REST| FastAPIApp
    Engines --> SQLiteDB
    Engines --> SMTP
    Engines --> GeminiAPI
```

### Technology Matrix
| Layer | Technologies Used | Key Libraries & Configurations |
|---|---|---|
| **Backend** | Python 3.11/3.12, FastAPI, Uvicorn | `pydantic v2`, `sqlalchemy 2.0`, `dnspython`, `beautifulsoup4`, `apscheduler`, `python-dotenv` |
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript | `tailwind-merge`, `lucide-react`, `clsx`, Static Export (`output: "export"`) |
| **Database** | SQLite 3 (Dev/Docker default) | Fully decoupled SQLAlchemy ORM models ready for PostgreSQL / Supabase connection |
| **Containerization** | Docker Multi-Stage Build | Node 20 builder -> Python 3.11 slim runner serving both API & static files on single port |
| **Deployment** | Render (Live Blueprint), Hostinger VPS, Netlify | Single container `$PORT` dynamic binding; `docker-compose.yml` with Nginx; `deploy.sh` |
| **Testing** | Pytest, FastAPI TestClient | 18 test files, 138 automated unit & integration test cases with 100% pass rate |

---

## 3. Monorepo Directory Layout & Key Files

```
D:\antigravity
├── .env.example                 # Template for application settings, API keys & SMTP
├── .gitignore                   # Ignores venvs, build caches, test databases
├── deploy.sh                    # 1-click VPS / Hostinger automated deployment script
├── docker-compose.yml           # Production multi-container spec (backend, frontend, nginx)
├── Dockerfile                   # Single unified all-in-one container for Render/cloud free tiers
├── Dockerfile.backend           # Dedicated FastAPI container
├── Dockerfile.frontend          # Dedicated Next.js frontend container
├── impex_leads.db               # Primary SQLite DB (72 verified buyers, 5 commodities, 6 deals)
├── netlify.toml                 # Root Netlify configuration with SPA redirect rules
├── PROJECT_HANDOVER.md          # This handover document
├── pytest.ini                   # Pytest test discovery configuration
├── README.md                    # Project overview and quickstart instructions
├── render.yaml                  # Render Infrastructure-as-Code Blueprint
│
├── backend/                     # FastAPI Backend Application
│   ├── requirements.txt         # Pinned Python package dependencies
│   ├── app/
│   │   ├── main.py              # Application entrypoint, CORS setup, StaticFiles mount
│   │   ├── api/                 # REST API Router endpoints
│   │   │   ├── __init__.py      # Combines all routers under /api/v1 prefix
│   │   │   ├── analytics.py     # KPI dashboard metrics, conversion funnels, CSV exports
│   │   │   ├── discovery.py     # UN Comtrade, APEDA connectors, DNS/TLS domain enricher
│   │   │   ├── health.py        # System health & database connectivity probe
│   │   │   ├── import_leads.py  # Bulk lead ingestion with duplicate prevention
│   │   │   ├── leads.py         # Lead CRUD, 100-pt verification, payment risk assessment
│   │   │   ├── outreach.py      # Mode A review queue, email approval/rejection, SMTP dispatch
│   │   │   ├── pipeline.py      # 15-stage Kanban board, deals management, Proforma Invoices
│   │   │   ├── products.py      # Exporter product profile management & live 5-factor matching
│   │   │   └── replies.py       # Incoming email webhook, 11-class NLP intent classifier
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic Settings reading environment variables
│   │   │   └── database.py      # SQLAlchemy engine, session maker, DB initialization
│   │   ├── models/              # SQLAlchemy Database ORM Models
│   │   │   ├── deal.py          # Deal, BuyerReply, ProformaInvoice models
│   │   │   ├── lead.py          # Lead model (verification scores, risk levels, provenance)
│   │   │   ├── outreach.py      # OutreachCampaign, OutreachEmail, SuppressionList models
│   │   │   ├── product_profile.py # ProductProfile model (specifications, HS codes, exclusions)
│   │   │   └── verification.py  # VerificationLog model (evidence audit trail)
│   │   ├── schemas/             # Pydantic Request & Response Data Schemas
│   │   │   ├── deal.py          # DealCreate, DealUpdate, KanbanBoardResponse, Funnel metrics
│   │   │   ├── lead.py          # LeadCreate, LeadResponse, BatchVerify schemas
│   │   │   ├── outreach.py      # EmailComposeRequest, ApprovalRequest, QueueSummary
│   │   │   ├── product_profile.py # ProductProfileCreate, QualificationResult schemas
│   │   │   ├── proforma.py      # ProformaInvoiceCreate, LineItem, ProformaInvoiceResponse
│   │   │   └── reply.py         # IncomingReplyRequest, ClassificationResult schemas
│   │   └── services/            # Core Business Logic & Algorithmic Engines
│   │       ├── batch_ingestion.py         # High-throughput lead batch processor
│   │       ├── domain_enrichment.py       # Live DNS MX, TLS cert & WHOIS verification
│   │       ├── email_composer.py          # Grounded AI email personalization composer
│   │       ├── embassy_directory_connector.py # MEA / Embassy commercial wing scraper
│   │       ├── followup_service.py        # 3-touch cadence engine, auto-halt on reply
│   │       ├── lead_discovery_crawler.py  # Ethical web crawler for buyer discovery
│   │       ├── lead_service.py            # Lead ingestion, deduplication hash generator
│   │       ├── linkedin_dork_service.py   # Procurement decision maker dork query builder
│   │       ├── payment_risk.py            # Commercial deal financial risk evaluator
│   │       ├── proforma_service.py        # DGFT/Customs commercial PI generator
│   │       ├── qualification_service.py   # 5-Factor product matching algorithm
│   │       ├── reply_classifier.py        # 11-Class NLP intent & entity extractor
│   │       ├── risk_service.py            # Lead-level payment fraud & scam guardian
│   │       ├── smtp_service.py            # Hostinger SMTP email dispatch & rate limiter
│   │       ├── trade_connectors.py        # UN Comtrade & APEDA API connectors
│   │       └── verification_service.py    # 100-Point Lead Verification rubric engine
│   ├── scripts/
│   │   └── seed_verified_real_buyers.py   # Seeds 72 real international buyers & 5 commodities
│   └── tests/                   # 138 Pytest Unit and Integration Tests
│       ├── conftest.py          # Test fixture setting isolated test_impex_runner.db
│       ├── test_all_services_sync.py
│       ├── test_api_endpoints.py
│       ├── test_day10_email_composer.py
│       ├── test_day11_smtp_dispatch.py
│       ├── test_day12_reply_intelligence.py
│       ├── test_day13_payment_and_reporting.py
│       ├── test_day14_security_hardening.py
│       ├── test_day3_day4.py
│       ├── test_day5_domain_enrichment.py
│       ├── test_day6_product_matching.py
│       ├── test_day7_verification_batch.py
│       ├── test_day8_risk_guardian.py
│       ├── test_day9_crm_pipeline.py
│       ├── test_followup_cadence_engine.py
│       ├── test_lead_generation_engine.py
│       ├── test_proforma_generator.py
│       └── test_verification_and_leads.py
│
├── frontend/                    # Next.js 14 Frontend Application
│   ├── package.json             # NPM dependencies & scripts
│   ├── next.config.mjs          # Static export configuration (output: "export")
│   ├── tailwind.config.ts       # Tailwind CSS design system configuration
│   └── src/
│       ├── app/
│       │   ├── globals.css      # Global styles and Tailwind directives
│       │   ├── layout.tsx       # Root layout with responsive navigation header
│       │   └── page.tsx         # Master interactive single-page dashboard
│       └── lib/
│           └── api.ts           # Unified TypeScript client for /api/v1 REST endpoints
│
└── nginx/
    └── default.conf             # Nginx reverse proxy configuration for VPS deployments
```

---

## 4. Database Models & Real Data Provenance

The production database is populated with **100% authentic international trade records**. No fictional or placeholder companies exist in the primary catalog.

### Authentic Indian Exporter Commodities Configured (`product_profiles` table)
| Profile ID | Product Name | HS Code | Origin | MOQ | Target Price | Target Markets | Preferred Payment Terms |
|---|---|---|---|---|---|---|---|
| `PROD-RICE-1121` | Indian 1121 Steam Basmati Rice | `1006.30.20` | India | 20 MT (1 FCL) | \$1,050 - \$1,200 / MT | UAE, Saudi Arabia, UK, USA, Kuwait | 30% Advance + 70% against BL scan / Irrevocable LC |
| `PROD-SPICE-TURM`| Alleppey Finger Turmeric (Curcumin 5%+) | `0910.30` | India | 5 MT | \$1,850 - \$2,200 / MT | Germany, Netherlands, USA, UK, Japan | 30% Advance + 70% against BL / 100% LC at Sight |
| `PROD-TEA-ASSAM` | Assam CTC Black Tea (Grade BP/BOP) | `0902.40` | India | 10 MT | \$3,200 - \$4,500 / MT | UK, Russia, UAE, Kazakhstan, Iran | Irrevocable LC at Sight or 50% Advance |
| `PROD-TEXT-COTTON`| 100% Combed Compact Cotton Yarn (30s/1) | `5205.12` | India | 18 MT (1 FCL) | \$3.40 - \$3.85 / KG | Bangladesh, Vietnam, Turkey, Portugal | 100% Irrevocable LC at Sight |
| `PROD-ENG-VALVES` | Industrial Forged Steel Valves (Class 800) | `8481.80.30` | India | 100 Units | \$45.00 - \$180.00 / Unit | UAE, Oman, Saudi Arabia, Qatar, Kuwait | 30% Advance + 70% against Shipping Documents |

### Verified International Buyer Records (`leads` table)
The database contains **72 verified real buyers** across the Middle East, Europe, North America, and Southeast Asia. Sourced directories include:
- **Al Maya Trading Co LLC (UAE)**: Dubai Chamber of Commerce, FMCG & Basmati importer.
- **Lulu Group International (UAE)**: Global Sourcing Division, agricultural & spice importer.
- **T. Choithram & Sons LLC (UAE)**: Importer of Indian rice, spices, and tea.
- **TRS Wholesale Co Ltd / Surya Foods (UK)**: Major South Asian ethnic food importer in London.
- **Heekeren & Co / Worlée NaturProdukte GmbH (Germany)**: European Spice Association member, importer of Alleppey Turmeric and ginger.
- **Ahmed Tea Ltd (UK)** & **Finlays (UK)**: Major British tea blending and packaging houses.
- **Square Textiles Ltd (Bangladesh)**: Major Dhaka textile manufacturing conglomerate importing Indian raw cotton and yarn.

---

## 5. Core Business Engines & Algorithmic Rubrics

### Engine 1: 100-Point Lead Verification Rubric
Located in [`backend/app/services/verification_service.py`](file:///d:/antigravity/backend/app/services/verification_service.py).
Evaluates leads without assumptions or fabrications.

$$\text{Buyer Verification Score} = S_{\text{identity}} + S_{\text{relevance}} + S_{\text{website}} + S_{\text{email}} + S_{\text{import}} + S_{\text{independent}}$$

| Scoring Category | Maximum Points | Criteria & Evidence Checked |
|---|---|---|
| **Identity Score** | 20 points | Company legal registration, official trade directory listing, chamber of commerce registration, verifiable corporate entity. |
| **Relevance Score** | 20 points | Explicit product category overlap, matching HS codes, verified commodity interest. |
| **Website Score** | 15 points | Domain alive check, HTTPS/TLS certificate valid (5 pts), live corporate website responding with HTTP 200 (10 pts). |
| **Email Score** | 15 points | Corporate business email domain check (15 pts). Disposable/free webmail (Gmail, Yahoo, Hotmail) penalized to max 2 pts with `FLAG_FREE_EMAIL_DOMAIN`. Live DNS MX record lookup via `dnspython`. |
| **Import Evidence** | 15 points | Verifiable bills of lading, customs port records, APEDA directory transaction history, or declared purchasing volume. |
| **Independent Evidence** | 15 points | Secondary supporting evidence: physical office address, telephone country code alignment, decision-maker LinkedIn presence. |

**Classification Tiers:**
- `Verified`: **80 – 100 points** (High priority candidate, ready for outreach)
- `Partially Verified`: **60 – 79 points** (Requires additional documentary check)
- `Unverified`: **< 60 points** (Insufficient evidence; outreach suppressed)

**Risk Levels:**
- `LOW`: Clean record, all domain & identity checks passed.
- `MEDIUM`: 2+ minor flags (e.g., missing direct phone, unindexed domain).
- `HIGH`: Free webmail used for corporate trade, or country of operation discrepancy.
- `CRITICAL`: Advance fee scam keywords, invalid NXDOMAIN, sanctioned trade entity.

---

### Engine 2: 5-Factor Product Matching Model
Located in [`backend/app/services/qualification_service.py`](file:///d:/antigravity/backend/app/services/qualification_service.py).
Calculates alignment between an exporter's commodity profile and a discovered buyer lead:

$$\text{Qualification Score} = W_{\text{prod}} + W_{\text{country}} + W_{\text{import}} + W_{\text{contact}} + W_{\text{readiness}}$$

| Factor | Weight | Scoring Logic & Guardrails |
|---|---|---|
| **1. Product Relevance** | 30 pts | Exact category match (30 pts); multi-token commodity overlap (24 pts); single keyword match (15 pts); HS code alignment (+5 pts). |
| **2. Country Alignment** | 25 pts | **Hard Disqualification Rule:** If buyer country matches exporter's `excluded_countries` list, score immediately drops to **0 pts** and lead is marked `Disqualified`. Target country match: 25 pts. Open non-priority destination: 12-18 pts. |
| **3. Import Evidence** | 20 pts | Documented import history of specific commodity: 20 pts. General import history: 15 pts. Official directory source: 10 pts. |
| **4. Contact Quality** | 15 pts | Corporate email domain: 7 pts. Decision-maker title (Director, Procurement, Sourcing): 5 pts. Verified phone & contact name: 3 pts. |
| **5. Verification Readiness** | 10 pts | Lead already marked `Verified` (score >= 80): 10 pts. `Partially Verified`: 6 pts. `Unverified`: 0-2 pts. |

---

### Engine 3: 15-Stage CRM & Financial Pipeline
Located in [`backend/app/models/deal.py`](file:///d:/antigravity/backend/app/models/deal.py) and [`backend/app/api/pipeline.py`](file:///d:/antigravity/backend/app/api/pipeline.py).
Tracks leads through the standard international export lifecycle:

```mermaid
stateDiagram-v2
    [*] --> Discovered
    Discovered --> VerificationPending
    VerificationPending --> VerifiedCandidate
    VerifiedCandidate --> Qualified
    Qualified --> OutreachApproved
    OutreachApproved --> EmailSent
    EmailSent --> BuyerReplied
    BuyerReplied --> RequirementsReceived
    RequirementsReceived --> QuotationPrepared
    QuotationPrepared --> Negotiation
    Negotiation --> PurchaseOrderReceived
    PurchaseOrderReceived --> PaymentVerification
    PaymentVerification --> OrderConfirmed
    OrderConfirmed --> Completed
    
    EmailSent --> LostOrRejected: Opt-out / No Interest
    Negotiation --> LostOrRejected: Price mismatch
    PaymentVerification --> LostOrRejected: Payment risk blocked
    Completed --> [*]
    LostOrRejected --> [*]
```

1. `Discovered`: Newly ingested raw lead.
2. `Verification Pending`: In automated 100-point audit queue.
3. `Verified Candidate`: Passed audit with score >= 80.
4. `Qualified`: Matched to exporter commodity profile.
5. `Outreach Approved`: Approved by human manager for email dispatch.
6. `Email Sent`: Dispatched via Hostinger SMTP.
7. `Buyer Replied`: Incoming inquiry registered via webhook or manual entry.
8. `Requirements Received`: Specific quantities, specifications, target delivery dates obtained.
9. `Quotation Prepared`: Formal DGFT-compliant Proforma Invoice generated.
10. `Negotiation`: Incoterms, payment terms, or volume discount discussions.
11. `Purchase Order Received`: Buyer issues formal purchase contract.
12. `Payment Verification`: LC received from advising bank or advance wire confirmed.
13. `Order Confirmed`: Commercial production / packaging scheduled.
14. `Completed`: Goods shipped, bill of lading released, final settlement realized.
15. `Lost / Rejected`: Disqualified, unverified, opted out, or deal abandoned.

---

### Engine 4: Payment Risk Guardian
Located in [`backend/app/services/payment_risk.py`](file:///d:/antigravity/backend/app/services/payment_risk.py).
Enforces commercial risk boundaries before financial commitments:
- **Separation of Concerns:** A buyer may have a high Qualification Score (95/100) but an unacceptable Payment Risk Profile. Both scores are tracked independently.
- **Secure Terms (Approved):** 100% Advance Wire, Confirmed Irrevocable LC at Sight.
- **Standard Terms (Requires Monitoring):** 30% Advance + 70% against BL scan, Irrevocable LC at Sight.
- **High-Risk Terms (Blocked by Default):** Open Account (OA 30, OA 60, OA 90), Documents against Acceptance (D/A), Unsecured Credit.
- **Action Rule:** Open Account terms for first-time buyers trigger a hard block with recommendation: *"Insist on 100% Irrevocable LC at Sight or minimum 30% Advance + 70% against BL scan. Never grant open account on initial order."*

---

### Engine 5: Mode A Assisted Outreach & Cadence Rules
Located in [`backend/app/services/email_composer.py`](file:///d:/antigravity/backend/app/services/email_composer.py) and [`backend/app/services/followup_service.py`](file:///d:/antigravity/backend/app/services/followup_service.py).
- **Mode A (Assisted / Human-in-the-Loop):** Every generated email is placed in the `Queued` state in `outreach_emails`. The export manager reviews the grounded email draft, edits if desired, and clicks "Approve" or "Reject". No automated emails are sent without human authorization.
- **3-Touch Export Cadence:**
  - **Touch 1 (Day 0):** Introduction, specific commodity specifications, origin details, and port of loading.
  - **Touch 2 (Day 4):** Polite follow-up, offer of Certificate of Analysis (CoA) or lab test samples.
  - **Touch 3 (Day 8):** Final inquiry, catalog retention request, polite disengagement.
  - **Strict Limit:** Exactly 3 touches maximum. No 4th email is ever generated.
- **Instant Auto-Halt:** Any incoming buyer reply, bounce, or opt-out automatically marks the lead `outreach_status = "Replied"` and cancels all pending/scheduled follow-up emails in the queue.
- **Suppression List:** Recipient emails marked "Not Interested" or "Unsubscribe" are written to the `suppression_list` table. Future emails to these addresses are blocked at the database level.

---

### Engine 6: 11-Class Buyer Reply Intelligence
Located in [`backend/app/services/reply_classifier.py`](file:///d:/antigravity/backend/app/services/reply_classifier.py).
Evaluates incoming emails and routes them to appropriate CRM stages:
1. `Interested Buyer` -> Stage: `Requirements Received`
2. `Request for Quotation` -> Stage: `Quotation Prepared`
3. `Request for Specs` -> Stage: `Requirements Received` (Prompts CoA dispatch)
4. `Samples` -> Stage: `Requirements Received` (Prompts sample courier dispatch)
5. `Price Negotiation` -> Stage: `Negotiation`
6. `Payment Terms` -> Stage: `Negotiation` (Triggers Payment Risk Guardian)
7. `Future Requirement` -> Stage: `Qualified` (Schedules future re-engagement)
8. `Not Interested` -> Stage: `Lost / Rejected` (Auto-adds to suppression list)
9. `Wrong Contact` -> Stage: `Discovered` (Prompts referral update)
10. `Potential Scam` -> Stage: `Lost / Rejected` (Auto-blocks lead with `CRITICAL` risk)
11. `Requires Human Review` -> Stage: Retains current stage (Flags for manager review)

**Entity Extraction:** Extracts regex/NLP entities for:
- Extracted Product Name
- Extracted Quantity (MT, KG, FCL)
- Extracted Target Price (USD / EUR)
- Extracted Delivery Port (CIF/FOB port)
- Extracted Payment Method (LC, Advance, CAD)

---

### Engine 7: DGFT-Compliant Proforma Invoice (PI) Generator
Located in [`backend/app/services/proforma_service.py`](file:///d:/antigravity/backend/app/services/proforma_service.py).
Generates official commercial export quotations:
- Includes Indian Exporter Details: IEC (Import Export Code), GSTIN, Bank AD Code, SWIFT Code, Bank Account Number.
- Consignee details: Buyer Company, Country, Address, Contact Person.
- Shipment details: Port of Loading (e.g., Nhava Sheva / JNPT Mumbai), Destination Port, Country of Origin (India), Incoterms (FOB/CIF/CFR).
- Line items: Description, HS Code, Quantity, Unit, Unit Price, Total Amount.
- Accessible via HTML endpoint: `GET /api/v1/deals/{deal_id}/proforma/html` for printing or PDF generation.

---

## 6. Complete REST API Reference

All backend API routes are prefixed with `/api/v1` and document interactive Swagger schemas at `/docs`.

### 1. Health & Diagnostics
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Service health status, database connection, and system timestamp |

### 2. Buyer Leads & Verification
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/leads` | Paginated lead listing with filters (`country`, `status`, `product`, `min_score`) |
| `POST` | `/api/v1/leads` | Ingest new lead with SHA-256 deduplication hash check |
| `GET` | `/api/v1/leads/review-queue` | Queue of leads requiring human review (partially verified or medium risk) |
| `GET` | `/api/v1/leads/high-risk` | High and Critical payment risk monitor |
| `POST` | `/api/v1/leads/verify-batch` | High-throughput batch verification runner (up to 500 leads) |
| `GET` | `/api/v1/leads/{lead_id}` | Fetch detailed lead profile by ID |
| `POST` | `/api/v1/leads/{lead_id}/verify` | Run automated 100-point verification audit on lead |
| `POST` | `/api/v1/leads/{lead_id}/verify-manual` | Human auditor override with audit trail logging |
| `GET` | `/api/v1/leads/{lead_id}/audit-trail` | Retrieve full historical verification logs for lead |
| `POST` | `/api/v1/leads/{lead_id}/risk-assessment` | Run payment fraud and risk assessment |
| `GET` | `/api/v1/leads/{lead_id}/risk-assessment` | Retrieve latest recorded risk assessment |

### 3. Exporter Product Profiles & Matching
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/products` | List all active exporter product profiles |
| `POST` | `/api/v1/products` | Create a new exporter product configuration |
| `GET` | `/api/v1/products/{product_id}` | Retrieve specific product profile specifications |
| `PUT` | `/api/v1/products/{product_id}` | Update product pricing, packaging, target markets, or exclusions |
| `DELETE` | `/api/v1/products/{product_id}` | Deactivate or delete product profile |
| `POST` | `/api/v1/products/{product_id}/match-leads` | Run 5-factor matching algorithm across all database leads |
| `POST` | `/api/v1/leads/{lead_id}/qualify/{product_id}` | Calculate match score between a specific lead and product |

### 4. CRM Pipeline & Deals Management
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/pipeline/kanban` | Full 15-stage Kanban board data (leads and commercial deals) |
| `GET` | `/api/v1/pipeline/summary` | Pipeline funnel metrics and realized commercial revenue |
| `PATCH` | `/api/v1/pipeline/leads/{id}/stage` | Transition lead across the 15 pipeline stages |
| `GET` | `/api/v1/deals` | List all commercial deals with status and value filtering |
| `POST` | `/api/v1/deals` | Create a new export deal linked to a verified lead |
| `GET` | `/api/v1/deals/{deal_id}` | Retrieve deal details, Incoterms, and financial values |
| `PATCH` | `/api/v1/deals/{deal_id}/stage` | Transition deal stage with audit trail logging |
| `PUT` | `/api/v1/deals/{deal_id}` | Update deal quotation amount, quantity, or terms |
| `DELETE` | `/api/v1/deals/{deal_id}` | Remove deal record |
| `POST` | `/api/v1/deals/{deal_id}/proforma` | Generate formal DGFT-compliant Proforma Invoice |
| `GET` | `/api/v1/deals/{deal_id}/proforma/html` | Render printable HTML export Proforma Invoice |

### 5. Mode A Assisted Outreach & Cadence
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/outreach/compose` | Generate grounded personalized outreach email draft |
| `GET` | `/api/v1/outreach/queue` | List emails awaiting human review or scheduled for dispatch |
| `GET` | `/api/v1/outreach/queue/summary` | Queue statistics (queued, approved, rejected, sent, replied) |
| `POST` | `/api/v1/outreach/emails/{id}/approve` | Manager approval to release email for SMTP dispatch |
| `POST` | `/api/v1/outreach/emails/{id}/reject` | Manager rejection with reason notes |
| `POST` | `/api/v1/outreach/dispatch` | Trigger rate-limited SMTP dispatch of all approved emails |
| `POST` | `/api/v1/outreach/cadence/process` | Check and queue due follow-ups (Touch 2 & 3) |
| `GET` | `/api/v1/outreach/cadence/status` | Current cadence funnel breakdown across all active sequences |
| `GET` | `/api/v1/outreach/suppression` | View suppressed email addresses and opt-outs |
| `POST` | `/api/v1/outreach/suppression` | Manually add email to suppression list |

### 6. Reply Intelligence & Webhook
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/replies/incoming` | Ingest raw incoming buyer email, classify intent, update CRM |
| `GET` | `/api/v1/replies` | List classified buyer replies |
| `GET` | `/api/v1/replies/{reply_id}` | Fetch classified reply details and extracted entities |
| `PATCH` | `/api/v1/replies/{reply_id}/review` | Human reviewer override of reply classification |

### 7. Trade Discovery & Market Intelligence
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/discover/comtrade` | Query UN Comtrade for top global import markets by HS code |
| `POST` | `/api/v1/discover/apeda` | Ingest APEDA directory records |
| `POST` | `/api/v1/discover/itp` | Ingest Indian Trade Portal records |
| `POST` | `/api/v1/discover/verify-website` | Verify company website availability and response |
| `POST` | `/api/v1/discover/enrich-domain` | Comprehensive DNS MX, TLS cert, and WHOIS domain check |

### 8. Analytics & CSV Export
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/analytics/dashboard` | Aggregated KPI metrics for admin overview |
| `GET` | `/api/v1/analytics/export/leads` | Export verified leads as CSV |
| `GET` | `/api/v1/analytics/export/deals` | Export commercial pipeline deals as CSV |

---

## 7. Environment Variables & Secrets Reference

All configurations are defined in `.env.example` and parsed through Pydantic Settings in [`backend/app/core/config.py`](file:///d:/antigravity/backend/app/core/config.py).

```bash
# ==============================================================================
# IMPEX AI — CONFIGURATION MATRIX
# ==============================================================================

# Application Settings
APP_NAME="Global Buyer Acquisition Engine"
APP_ENV="production"                # "development" | "production"
DEBUG=False
PORT=8000                           # Dynamically overridden by $PORT on Render
HOST="0.0.0.0"

# Database Configuration
# Local SQLite default: sqlite:///./impex_leads.db
# Supabase / PostgreSQL: postgresql://postgres:password@db.supabase.co:5432/postgres
DATABASE_URL="sqlite:///./impex_leads.db"

# Security & CORS
SECRET_KEY="generate-a-strong-random-secret-key-for-jwt-and-csrf"
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALLOWED_ORIGINS="*"                 # In prod: "https://yourdomain.com,https://impex-ai.onrender.com"

# AI / LLM Configuration
AI_PROVIDER="gemini"                # "gemini" | "openai" | "mock"
GEMINI_API_KEY=""                   # Google Gemini API key (optional, template fallback active)
OPENAI_API_KEY=""                   # OpenAI API key (if provider=openai)
LLM_MODEL="gemini-1.5-pro"

# Email Sending (Hostinger / Standard Corporate SMTP)
SMTP_HOST="smtp.hostinger.com"
SMTP_PORT=465                       # 465 for SSL, 587 for TLS
SMTP_USER="export@yourdomain.com"   # Your Hostinger webmail address
SMTP_PASSWORD=""                    # Your Hostinger email password
SMTP_FROM_NAME="Indian Export Corp"
SMTP_FROM_EMAIL="export@yourdomain.com"
SMTP_USE_SSL=True

# Outreach Safety & Anti-Spam Guardrails
DAILY_SEND_LIMIT=50                 # Maximum emails per day
HOURLY_SEND_LIMIT=10                # Maximum emails per hour
DEFAULT_OUTREACH_MODE="assisted"    # "assisted" (Mode A - Manual Approval) or "automated"
ENABLE_AUTO_FOLLOWUPS=False         # Requires explicit manager activation

# External Trade APIs (Optional / Free Tiers)
UN_COMTRADE_API_KEY=""
APEDA_PORTAL_USER=""
DGFT_PORTAL_USER=""
```

---

## 8. Deployment Architecture & Operational Runbooks

### Option A: Render 1-Click Unified Blueprint (Active Production)
- **Live URL:** [https://impex-ai.onrender.com](https://impex-ai.onrender.com)
- **Architecture:** The root [`Dockerfile`](file:///d:/antigravity/Dockerfile) uses a multi-stage build:
  1. Compiles Next.js 14 frontend into static assets (`npm run build` -> `frontend/out`).
  2. Copies static assets into Python 3.11 container.
  3. FastAPI automatically mounts `frontend/out` to `/` via `StaticFiles(directory=static_dir, html=True)`.
  4. Binds dynamically to Render's assigned port (`${PORT:-8000}`).
  5. Both UI and API run on the exact same origin, eliminating CORS issues.
- **Blueprint File:** [`render.yaml`](file:///d:/antigravity/render.yaml).

### Option B: Hostinger / Dedicated Linux VPS Deployment
The repository includes a ready-to-run Docker Compose and Nginx configuration:
1. SSH into VPS:
   ```bash
   ssh root@your-vps-ip
   ```
2. Clone repository:
   ```bash
   git clone https://github.com/Vaibhav3525/impex-ai.git /var/www/impex-ai
   cd /var/www/impex-ai
   ```
3. Run automated deployment script:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```
   The script verifies Docker, copies `.env`, runs database seeders, compiles Nginx reverse proxy configurations, and launches the stack with auto-restart on system reboot.

### Option C: Local Development Runbook
1. **Backend Setup:**
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python scripts/seed_verified_real_buyers.py
   python -m uvicorn app.main:app --reload --port 8000
   ```
2. **Frontend Setup:**
   ```powershell
   cd frontend
   npm install
   npm run dev
   # Opens at http://localhost:3000
   ```
3. **Execute Test Suite (138 Tests):**
   ```powershell
   $env:PYTHONPATH="backend"
   & "backend/venv/Scripts/python.exe" -m pytest backend/tests -q
   # Expected result: 138 passed in ~13s
   ```

---

## 9. Immediate Roadmap & Action Items for Codex

When picking up development, Codex or the subsequent development team should prioritize the following tasks:

### Priority 1: Connect Production SMTP Credentials
- In [`render.yaml`](file:///d:/antigravity/render.yaml) or Render Dashboard Environment Variables:
  - Set `SMTP_USER` to the official business email (e.g., `exports@yourcompany.com`).
  - Set `SMTP_PASSWORD` to the Hostinger email password.
  - Set `SMTP_FROM_EMAIL` to match `SMTP_USER`.
- Test real email dispatch by navigating to the Outreach tab, approving an email, and clicking "Dispatch Approved Emails".

### Priority 2: Connect Live Gemini 1.5 Pro API Key
- Provide a valid `GEMINI_API_KEY` in environment variables.
- The composer in [`email_composer.py`](file:///d:/antigravity/backend/app/services/email_composer.py) will automatically switch from the deterministic template fallbacks to live, hyper-personalized generative copy while preserving grounding evidence.

### Priority 3: Migrate to Supabase / Managed PostgreSQL
- ImpEx AI uses SQLAlchemy 2.0 with zero SQLite-specific dialect features.
- To migrate to Supabase:
  1. Create a Supabase project.
  2. Retrieve the pooled connection string: `postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres`.
  3. Update `DATABASE_URL` in `.env` or Render environment settings.
  4. Run `python scripts/seed_verified_real_buyers.py` to initialize tables and load the authentic buyer dataset.

### Priority 4: Production Custom Domain & SSL
- In Render Dashboard -> Settings -> Custom Domains:
  - Add your custom domain (e.g., `impex.yourdomain.com`).
  - Add the CNAME DNS record pointing to Render's ingress URL.
  - Render automatically provisions a free Let's Encrypt wildcard SSL certificate.

### Priority 5: Expand Automated Discovery Crawlers
- Review [`backend/app/services/embassy_directory_connector.py`](file:///d:/antigravity/backend/app/services/embassy_directory_connector.py) and [`backend/app/services/lead_discovery_crawler.py`](file:///d:/antigravity/backend/app/services/lead_discovery_crawler.py).
- Add scrapers for additional Export Promotion Councils (e.g., FIEO, EEPC India for engineering goods, TEXPROCIL for cotton textiles).

---

## 10. Verification & Audit Trail Summary

| Component | Status | Verification Evidence |
|---|---|---|
| **FastAPI Backend** | Operational | `/api/v1/health` returns `{"status":"healthy","database":"connected"}` |
| **Next.js Dashboard** | Operational | Clean rendering, zero hydration errors, interactive modals functional |
| **Database Integrity** | Verified | 72 real buyers, 5 authentic commodities, 6 active deals in `impex_leads.db` |
| **Verification Engine** | Passing | 100-point rubric with DNS MX & TLS checking verified in unit tests |
| **Matching Engine** | Passing | 5-factor scoring with exclusion enforcement verified in unit tests |
| **Payment Risk Guardian**| Passing | High-risk terms blocked; secure LC/Advance approved |
| **Mode A Outreach** | Passing | Emails queued for review; auto-halt on reply validated |
| **Test Suite** | 100% Pass | 138/138 tests passing (`pytest backend/tests -q`) |
| **Render Cloud Deployment**| Live | Deployed at `https://impex-ai.onrender.com` |
| **Git Repository** | Up to date | Branch `master` tracking `origin/master` at `Vaibhav3525/impex-ai` |

*Handover specification prepared and validated for Codex / engineering team.*
