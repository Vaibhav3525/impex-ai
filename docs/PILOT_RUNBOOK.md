# Pilot Operational Runbook: 10-Step Exporter Workflow

## AI-Powered Global Import–Export Buyer Acquisition & Automation System

This runbook guides an Indian exporter through the complete commercial lifecycle: from configuring their export catalog to securing verified buyer inquiries and closing safe international sales orders.

---

## 1. Complete Workflow Diagram

```
[ Step 1: Product Profile ] ──> [ Step 2: Ingest Discovered Leads ]
                                            │
                                            ▼
[ Step 4: Review Queue ]   <─── [ Step 3: 100-Pt Verification ]
           │                                │
           ▼                                ▼
[ Step 5: Risk Guardian ]  ───> [ Step 6: Grounded AI Sequence ]
                                            │
                                            ▼
[ Step 8: SMTP Dispatch ]  <─── [ Step 7: Mode A Human Approval ]
           │
           ▼
[ Step 9: Inbound Reply (11 Classes) ] ──> [ Step 10: Deal & Financial Risk ]
```

---

## 2. Step-by-Step Pilot Instructions

### Step 1: Configure Exporter Product Profile
Before discovering buyers, define your exact export commodity parameters:
1. Open the UI at `http://localhost:3000` or invoke `POST /api/v1/products`.
2. Fill in:
   - **Product Name:** e.g., *Basmati Rice 1121 Steam Grade*
   - **HS Code:** e.g., *1006.30*
   - **Origin:** *India*
   - **Target Countries:** e.g., *["Saudi Arabia", "United Arab Emirates", "United Kingdom", "Germany"]*
   - **Excluded Countries:** e.g., *["North Korea", "Iran"]* (triggers automatic hard disqualification)
   - **MOQ & Price:** e.g., *25 Metric Tons (1x20ft Container)*, *USD 1,150 / MT FOB Mundra*
   - **Payment Terms:** *30% Advance + 70% against Bill of Lading scan* or *100% Irrevocable LC at Sight*

### Step 2: Ingest Candidate International Buyers
Acquire initial buyer leads through compliant channels:
1. **Official CSV Upload:** Navigate to the **Import Leads** tab. Upload an official buyer roster (APEDA directory, Trade Portal export, or trade mission list).
2. **Trade Connectors:** Run `POST /api/v1/discover/apeda` or `POST /api/v1/discover/indian-trade-portal` with category keywords.
3. **Deduplication Engine:** System generates an immutable SHA-256 hash `sha256(company_normalized + country/domain)`. Existing records are updated with new data; duplicates are safely rejected without count inflation.

### Step 3: Run 100-Point Evidence Verification
Evaluate the technical and trade authenticity of discovered buyers:
1. Trigger batch verification via `POST /api/v1/leads/verify-batch?limit=100`.
2. The 100-point rubric evaluates:
   - *Company Identity & Registration Evidence (20 pts)*
   - *Product & Industry Relevance (20 pts)*
   - *Website & Business Identity Consistency (15 pts)*
   - *Business Corporate Email MX/SMTP (15 pts)*
   - *Documented Import/Purchasing Activity (15 pts)*
   - *Independent Supporting Signals (15 pts)*
3. Review audit logs: Each buyer record includes an immutable audit log detailing every point scored.

### Step 4: Clear the Manual Review Queue
Address uncertain or borderline leads:
1. Click **Review Queue** (`GET /api/v1/leads/review-queue`) for candidates scoring between 60.0 and 79.9 pts.
2. A human compliance officer inspects external evidence (company registry, trade directory link).
3. Click **Override Status** (`POST /api/v1/leads/{id}/verify-manual`) to mark as *Verified* or *Rejected* with mandatory justification notes.

### Step 5: Scan with Payment Risk Guardian
Protect against international export fraud before engaging in outreach:
1. Inspect the **High Risk Queue** (`GET /api/v1/leads/high-risk`).
2. The engine scans for:
   - `FLAG_ADVANCE_FEE_SCAM`: Solicitations involving upfront registration fees, attorney certifications, or tender guarantee deposits.
   - `FLAG_THIRD_PARTY_PAYER`: Divergent paying entities or offshore escrow accounts.
   - `FLAG_COUNTRY_MISMATCH`: Discrepancy between stated buyer country and website ccTLD.
   - `FLAG_DOMAIN_AGE_UNDER_90_DAYS`: Newly registered spoofing domains.
3. *Critical Rule:* A high qualification score never cancels a fraud flag. Leads with `CRITICAL` risk are permanently blocked from outreach.

### Step 6: Generate Grounded AI Email Sequences
Create culturally aligned, factual introduction emails:
1. Select a qualified lead and call `POST /api/v1/outreach/{lead_id}/compose`.
2. Choose Sequence:
   - **Step 1 (Day 1):** Professional Introduction & Product Catalog (localized: *Sehr geehrte(r)* for Germany, *Sama* for Japan, formal titles for Middle East).
   - **Step 2 (Day 4):** Factual Quality Specifications & Certifications (HACCP, FSSAI, ISO, phytosanitary specs).
   - **Step 3 (Day 8):** Courteous Commercial Closing & Sample Inquiry.
3. *Grounding Guarantee:* The composer draws solely from verified lead data and exporter profile parameters. Zero hallucinations.

### Step 7: Mode A (Assisted) Human Signoff
Enforce mandatory human oversight:
1. Navigate to the **Outreach Queue** (`GET /api/v1/outreach/queue`).
2. All generated emails reside in status `Queued`.
3. The export manager reviews recipient email, subject, and personalized body.
4. Click **Approve** (`POST /api/v1/outreach/emails/{id}/approve`) or **Reject** with feedback.

### Step 8: Controlled SMTP Dispatch & Deliverability
Dispatch emails while preserving domain reputation:
1. Trigger dispatch (`POST /api/v1/outreach/dispatch-batch?limit=10`).
2. Built-in rate limiter enforces:
   - Max 10 emails per rolling 60-minute window.
   - Max 50 emails per rolling 24-hour day.
3. Recipient suppression check: If a recipient domain or address has unsubscribed or hard-bounced, dispatch is blocked instantly.
4. On success, the CRM lead stage automatically updates to `Email Sent`.

### Step 9: Inbound Reply Classification & Entity Extraction
When a buyer responds:
1. Ingest reply via webhook or manual input (`POST /api/v1/replies/incoming`).
2. The AI classifier categorizes into one of 11 canonical classes:
   - *Interested Buyer*, *Request for Quotation (RFQ)*, *Request for Specs*, *Samples*, *Price Negotiation*, *Payment Terms*, *Future Requirement*, *Not Interested*, *Wrong Contact*, *Potential Scam*, *Requires Human Review*.
3. Automatically extracts:
   - Desired Quantity (e.g., *2x40ft containers*)
   - Target Price (e.g., *USD 1,120 / MT*)
   - Destination Port (e.g., *Jebel Ali, Dubai*)
   - Preferred Payment Method (e.g., *LC at Sight*)
4. Qualified buyer replies automatically advance the CRM pipeline stage to `Buyer Replied` or `Requirements Received`.

### Step 10: Deal Structuring & Financial Risk Audit
Safeguard export transactions before production commitment:
1. Create export deal (`POST /api/v1/deals`) with Incoterms and quotation amounts.
2. Run Financial Risk Assessment (`POST /api/v1/deals/{deal_id}/financial-risk`).
3. **Safety Rules:**
   - **Open Account (OA 30/60/90) or D/A:** Blocked by default for new buyers. System mandates 100% Irrevocable LC at Sight or 30% Advance + 70% against BL.
   - **Exposure > USD 100,000:** Flags capital exposure and mandates executive director approval and ECGC export credit insurance coverage.
4. When buyer confirms purchase order and advance payment/LC is advised:
   - Advance stage to `Order Confirmed`.
   - Realized export revenue is verified and reflected in the **Executive Performance Report** (`GET /api/v1/analytics/executive-report`).

---

## 3. Daily Operational Checklist for Exporter

| Time | Action | Screen / Endpoint |
| :--- | :--- | :--- |
| **09:30 AM** | Review previous day's inbound buyer replies | `/api/v1/replies?reviewed_status=PENDING` |
| **10:15 AM** | Inspect and resolve candidates in Review Queue | `/api/v1/leads/review-queue` |
| **11:00 AM** | Review and Approve queued outbound emails (Mode A) | `/api/v1/outreach/queue` |
| **11:30 AM** | Trigger batch dispatch (hourly cap auto-managed) | `/api/v1/outreach/dispatch-batch` |
| **03:00 PM** | Audit deal financial terms & payment structures | `/api/v1/deals/{id}/financial-risk` |
| **05:30 PM** | Pull daily Executive KPI Report | `/api/v1/analytics/executive-report` |

