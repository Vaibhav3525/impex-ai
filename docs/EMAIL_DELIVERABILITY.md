# International Email Deliverability & Anti-Spam Compliance Guide

## 1. Authentication Infrastructure (Mandatory DNS Records)

To ensure high inbox placement across international corporate mail servers (Google Workspace, Microsoft 365, European corporate gateways), your sending domain must configure SPF, DKIM, and DMARC:

### A. SPF (Sender Policy Framework)
Add a `TXT` record at your domain apex (`example.com`):
```text
v=spf1 include:_spf.hostinger.com ~all
```
*(Replace `_spf.hostinger.com` with your SMTP provider's SPF include)*

### B. DKIM (DomainKeys Identified Mail)
Generate a 2048-bit DKIM keypair in your cPanel/Hostinger portal and publish the public key:
```text
Name: default._domainkey.example.com
Type: TXT
Value: v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
```

### C. DMARC (Domain-based Message Authentication, Reporting & Conformance)
Publish a DMARC policy at `_dmarc.example.com`:
```text
Name: _dmarc.example.com
Type: TXT
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@example.com; pct=100; sp=quarantine
```

---

## 2. IP & Domain Warm-Up Schedule

Never dispatch 500 emails on day 1 from a fresh domain or IP. Follow this recommended ramp-up:

| Week | Daily Send Limit | Hourly Cap | Target Profile |
|---|---|---|---|
| **Week 1** | 10 emails/day | 3 emails/hr | Highly verified candidates (Score >= 90) |
| **Week 2** | 25 emails/day | 5 emails/hr | Verified buyers with direct import history |
| **Week 3** | 50 emails/day | 10 emails/hr | Qualified prospects in target countries |
| **Week 4+** | 100 emails/day | 15 emails/hr | Scaled outreach with active response tracking |

---

## 3. Deliverability Health Thresholds

| Metric | Target | Action If Breached |
|---|---|---|
| **Bounce Rate** | < 2.0% | Immediately pause campaigns. Run DNS MX & SMTP handshake verification on all pending leads. |
| **Spam Complaints** | < 0.1% | Review email personalization grounding. Ensure Mode A human approval is enabled for all emails. |
| **Open Rate** | > 35.0% | Test alternative professional subject lines focused on specific commodity grade and origin port. |
| **Reply Rate** | > 8.0% | Review commercial terms, MOQ, and sample shipment offers. |

---

## 4. Legal Compliance Guidelines

### CAN-SPAM Act (United States)
- Provide a clear, conspicuous physical postal address in the footer of all emails.
- Honor all opt-out / unsubscribe requests within 10 business days (enforced automatically via `SuppressionList`).
- Accurate From header and truthful subject lines (strictly enforced by zero-fabrication grounding engine).

### GDPR (European Union)
- **Lawful Basis:** Article 6(1)(f) Legitimate Interest for B2B commercial trade communications.
- Direct emails must be relevant to the recipient's professional corporate procurement duties.
- Recipient must be provided with an immediate right to object / unsubscribe.

### Indian Information Technology Act (2000 & Amendments)
- Accurate sender identity and origin details.
- No deceptive transmission headers.
