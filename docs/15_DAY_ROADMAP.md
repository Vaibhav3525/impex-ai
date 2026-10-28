# 15-Day MVP Milestone Roadmap & Delivery Schedule

## Target
Deliver a production-ready, fully functional MVP of the **AI-Powered Global Import–Export Buyer Acquisition & Automation System** on Windows 11 with complete documentation, zero-hallucination verification engine, and controlled outreach.

---

| Phase | Day | Focus | Target Deliverables & Verification Criteria | Status |
| :---: | :---: | :--- | :--- | :---: |
| **Phase 1: Architecture & Foundation** | **Day 1** | Requirements & System Architecture | - PRD confirmation & system architecture document<br/>- Repository scaffolding (`backend/`, `frontend/`, `docs/`)<br/>- Data Source Register & Verification Rubric<br/>- Environment template (`.env.example`) & Git initialization | **IN PROGRESS** |
| | **Day 2** | Database Schema & API Foundation | - SQLAlchemy 2.0 ORM models for Leads, Verification, Campaigns, Deals<br/>- SQLite / PostgreSQL dual-driver setup<br/>- FastAPI application setup with OpenAPI docs and health check endpoints | Planned |
| | **Day 3** | Lead Ingestion & Deduplication | - 20-field lead normalization pipeline<br/>- Multi-key deduplication engine (Company Name + Domain + Tax ID hash)<br/>- Batch lead upload (CSV / JSON) with validation error reporting | Planned |
| **Phase 2: Discovery & Matching** | **Day 4** | Government Trade Source Connectors | - Ingestion adapter for APEDA / DGFT public buyer directories<br/>- UN Comtrade API integration for market-level country validation<br/>- Source evidence attribution tracker | Planned |
| | **Day 5** | Company Discovery & Web Scanner | - Company website alive check (HTTP 200, TLS/SSL)<br/>- Automated public `/contact` and `/about` parser<br/>- Domain WHOIS registration age checker | Planned |
| | **Day 6** | Product & Country Matching | - Admin product configuration UI & API (HS code, MOQ, specs, origin)<br/>- Exporter-to-buyer compatibility scoring algorithm<br/>- Match explanation generator ("Why this buyer was qualified") | Planned |
| **Phase 3: Verification & Risk Engine** | **Day 7** | 100-Point Verification Engine | - DNS MX record lookup and SMTP handshake verifier<br/>- Corporate registry cross-check connector<br/>- Complete audit trail logging with timestamps and source URLs | Planned |
| | **Day 8** | Risk Scoring & Fraud Flags | - Automated anomaly detection (Domain age <90d, free email domains)<br/>- Third-party bank mismatch detection<br/>- Separate Qualification Score vs Payment Risk Score | Planned |
| | **Phase 4: Outreach & CRM** | **Day 9** | CRM Pipeline & Review Queue | - 15-stage CRM Kanban board & lead table<br/>- Mode A "Assisted Outreach" review queue with 1-click approvals<br/>- Filter by product, country, verification tier, and risk flags | Planned |
| | **Day 10** | AI Email Personalization Engine | - Contextual email generation grounded strictly in verified buyer data<br/>- Product specification and incoterms injection<br/>- 3-step cadence engine (Day 1 Intro, Day 4 Follow-up, Day 8 Wrap-up) | Planned |
| | **Day 11** | SMTP Dispatch & Compliance | - Hostinger / SMTP integration with TLS<br/>- Hourly and daily sending rate limiters<br/>- Hard bounce detection and permanent suppression list | Planned |
| **Phase 5: Response Intelligence** | **Day 12** | Reply Classification Engine | - 11-category AI email response classifier<br/>- Key entity extraction (Quantity, Target Price, Delivery Port, Terms)<br/>- Automatic follow-up cancellation on buyer reply | Planned |
| | **Day 13** | Payment Risk & Reporting Dashboard | - Payment risk review module (LC, D/P, D/A, Open Account checks)<br/>- Admin dashboard with conversion KPI tracking<br/>- Lead quality score distribution charts | Planned |
| **Phase 6: Testing & Launch** | **Day 14** | End-to-End Hardening & Security | - End-to-end integration testing of discovery -> verify -> outreach -> reply<br/>- Rate-limiting & secret leakage audit<br/>- Load testing against 500 records/day processing target | Planned |
| | **Day 15** | Pilot Launch & System Handover | - Live test campaign in Mode A (Assisted Outreach)<br/>- Delivery of complete source code, installation guide, and runbook<br/>- Post-launch maintenance and optimization plan | Planned |

