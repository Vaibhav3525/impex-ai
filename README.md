# AI-Powered Global Import–Export Buyer Acquisition & Automation System

[![Architecture: FastAPI + Next.js](https://img.shields.io/badge/Stack-FastAPI%20%2B%20Next.js-blue.svg)](https://fastapi.tiangolo.com)
[![Status: MVP In Development](https://img.shields.io/badge/Status-Day%201%20Foundation-brightgreen.svg)]()
[![Compliance: Legal Trade Data](https://img.shields.io/badge/Compliance-Strict%20Opt--In%20%26%20Public%20Sources-orange.svg)]()

A high-precision, evidence-backed platform that automates international buyer discovery, verification, qualification scoring, personalized outreach, and deal pipeline management for exporters.

---

## 🎯 Core Conversion Funnel

The system is optimized for real business conversion, not raw unverified email volume:

$$\textbf{Verified Relevant Buyers} \longrightarrow \textbf{Qualified Inquiries} \longrightarrow \textbf{Quotations} \longrightarrow \textbf{Confirmed Orders} \longrightarrow \textbf{Actual Revenue}$$

---

## 🚀 Key Capabilities

- **Modular Discovery Engine**: Integrates with authorized public trade directories, government portals (DGFT, APEDA, MEA, Indian Trade Portal, UN Comtrade), and verified company registries.
- **100-Point Buyer Verification Engine**: Multi-stage identity, website, domain MX/DNS, registry, and import evidence checks. Enforces strict zero-hallucination rules.
- **Dual Qualification & Risk Scoring**: Keeps business match score separate from fraud/payment risk indicators.
- **Assisted Outreach (Mode A)**: AI generates hyper-personalized, context-grounded business proposals placed in a 1-click human review queue.
- **11-Class Reply Intelligence**: Automated parsing of incoming buyer responses, extracting required quantity, target price, incoterms, and requested certifications.
- **Payment Risk Guardian**: Evaluates risk profiles across Advance, LC, D/P, D/A, and Open Account before any commercial commitments.
- **15-Stage CRM Deal Pipeline**: End-to-end prospect tracking from discovery through quotation to confirmed order.
- **Daily Performance Dashboard**: Real-time conversion tracking, quality score distributions, and operational cost metrics.

---

## 🏗️ System Architecture

```
d:\antigravity\
├── backend/                  # Python 3.11+ / FastAPI Core Service
│   ├── app/
│   │   ├── api/              # REST Endpoints (Leads, Verification, Campaigns, Deals, Analytics)
│   │   ├── models/           # SQLAlchemy 2.0 Database Models
│   │   ├── schemas/          # Pydantic v2 Request/Response Schemas
│   │   ├── services/         # Business Engines (Discovery, Verification, Scoring, Outreach, AI)
│   │   ├── core/             # Configuration, Security, and Database Session
│   │   └── main.py           # FastAPI Application Entrypoint
│   ├── requirements.txt      # Backend Dependencies
│   └── tests/                # Automated Unit & Integration Tests
├── frontend/                 # Next.js 14+ / React / Tailwind CSS
│   ├── src/
│   │   ├── app/              # App Router Pages (Dashboard, Leads, Review Queue, Campaigns, Pipeline)
│   │   ├── components/       # UI Components & Kanban Boards
│   │   └── lib/              # API Client & State Hooks
│   ├── package.json
│   └── tailwind.config.ts
├── docs/                     # Engineering & Compliance Documentation
│   ├── ARCHITECTURE.md       # High-level architecture and flow diagrams
│   ├── DATA_SOURCES.md       # Authorized source register, terms, and costs
│   ├── VERIFICATION_ENGINE.md# 100-point rubric and risk evaluation logic
│   └── 15_DAY_ROADMAP.md     # Day 1 - Day 15 milestone roadmap
├── .env.example              # Environment variables template
├── .gitignore
└── README.md
```

---

## 🛠️ Quick Start (Local Development)

### 1. Backend Setup
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API Documentation will be live at: `http://localhost:8000/docs`

### 2. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Dashboard UI will be live at: `http://localhost:3000`

---

## 🛡️ Ethics, Privacy & Anti-Spam Compliance

1. **No Data Fabrication**: Contact information is never invented or simulated. Missing data is tagged as missing.
2. **Authorized Sources Only**: Strictly respects robots.txt, platform terms, and public domain data rules.
3. **Opt-Out & Suppression**: Permanent suppression list prevents unwanted contact.
4. **Human in the Loop**: High-risk payment terms and first outreach campaigns require manual human authorization.
