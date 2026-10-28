# Operating Cost Analysis & Economic Estimate

## AI-Powered Global Import–Export Buyer Acquisition & Automation System

PRD §2 & §14 Requirement: *"Maintain low operating costs through free data sources and open-source tools wherever practical."*

---

## 1. Executive Summary

Traditional international trade development relies on high-overhead intermediaries, commercial buyer subscription platforms, or physical trade fair exhibitions. This system leverages **official public trade registries, government export bodies (DGFT, APEDA, Indian Trade Portal), open-source protocol inspection, and deterministic grounded templates**, reducing operational costs by over **99%**.

---

## 2. Monthly Operating Cost Breakdown (MVP Architecture)

| Component | Architecture Choice | Cost per Month | Notes |
| :--- | :--- | :--- | :--- |
| **Data Ingestion** | Official Trade Connectors (APEDA, DGFT, Indian Trade Portal, UN Comtrade free tier) | **$0.00** | Free public trade registries and official directories. |
| **Domain & DNS Verification** | Native `dnspython` MX query + socket EHLO probe | **$0.00** | Direct local network inspection; zero external API charges. |
| **Identity & WHOIS Age** | Native `python-whois` protocol query | **$0.00** | Direct WHOIS port 43 client query. |
| **Database Storage** | Local SQLite (migratable to Postgres) | **$0.00** | Zero cloud database management fees during pilot. |
| **Email Personalization** | Grounded Template Engine (Sequences 1, 2, 3) | **$0.00** | Deterministic factual template formatting with zero hallucination. |
| **AI LLM Fallback (Optional)**| Google Gemini 1.5 Flash / OpenAI API | **~$1.00 – $3.00** | Only utilized if unstructured reply extraction requires LLM parsing. |
| **SMTP Dispatch** | Exporter's existing business domain (Google Workspace / Microsoft 365) | **$0.00** | Utilizes existing outbound corporate email quotas (10–50 emails/day). |
| **Hosting & Execution** | Local Windows 11 workstation | **$0.00** | Runs locally without cloud VPS overhead. |
| **TOTAL ESTIMATED MONTHLY COST** | | **$0.00 – $3.00** | **Virtually zero marginal operating expense.** |

---

## 3. Comparison with Traditional Trade Acquisition Methods

| Method | Upfront Investment | Recurring Monthly Cost | Time to Deploy | Data Transparency |
| :--- | :--- | :--- | :--- | :--- |
| **International Trade Fairs** (Gulfood, SIAL, Anuga) | $10,000 – $25,000 (booth, flights, samples) | N/A (Event-based) | 4–6 months planning | High interaction, but brief duration and zero automated follow-up. |
| **Commercial B2B Databases** (Panjiva, ImportGenius) | $0 | $300 – $900 / month | 1 day | Historical customs manifests only; often outdated contacts. |
| **Commission Export Brokers** | None upfront | 3% – 8% commission on total shipment value | 1–3 months | Intermediary controls buyer relationship; exporter has zero visibility. |
| **This Automation System** | **$0** | **$0 – $3 / month** | **Instant (15-Day MVP)** | **100% transparent audit trail, full CRM ownership, zero commission.** |

---

## 4. Scalability & High-Volume Cost Projections

When scaling up to **500 new lead records per day** (15,000 leads per month):

- **Local DNS & Network Probing:** Zero incremental cost (standard broadband bandwidth).
- **SQLite Concurrency:** Up to 100,000 leads easily handled in local SQLite database file with WAL mode enabled.
- **Dedicated VPS (Optional Future Upgrade):** $10 – $20/month (e.g., Hetzner / DigitalOcean) if migrated to 24/7 cloud server.
- **Dedicated SendGrid / Amazon SES (Optional Future Upgrade):** ~$1.50 per 10,000 emails dispatched if external transactional relay is preferred.

---

## 5. Risk & Compliance Disclaimer

1. **No Guaranteed Commercial Return:** The system accelerates discovery, verification, and grounded outreach, but commercial trade success depends on product quality, competitive pricing, buyer market conditions, and international regulatory compliance.
2. **Anti-Spam & Deliverability Protection:** By strictly capping volume (max 10 emails/hour, max 50 emails/day) and enforcing Mode A human signoff, the exporter avoids IP reputation damage and costly domain burn.

