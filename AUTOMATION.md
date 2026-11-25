# Running automation

Start the dashboard with `./start-local.ps1`, then start its worker in a separate PowerShell session with `./start-worker.ps1`. Both processes use the same `.env` and database. The worker stays paused until an authenticated operator chooses **Start automation** in **Automation & campaigns**. Starting a worker process alone never authorizes email.

For a single scheduled invocation, set `PYTHONPATH=backend` and run `python -m app.worker --once` from this directory. The continuous worker checks every 30 seconds and runs a due cycle every `AUTOMATION_INTERVAL_SECONDS` (default 600). Due times and cycle ownership are persisted in the database. Use one worker; a ten-minute database lease prevents overlapping cycle execution. Runs interrupted by a crash are identified on recovery. Existing `Sending` or `Delivery Unknown` emails require investigation and are never automatically retried.

## Campaign authorization

1. Review product facts, certifications, prices and price units through **Review records**. Configure `EXPORTER_NAME` and the actual sender address in `.env`.
2. Create a campaign draft for one product, an explicit list of countries, and a daily limit (1–50 messages, including follow-ups).
3. Read all three message previews and authorize the campaign. The current operator is recorded. Authorization expires after 30 days in the UI (API supports 1–90 days).
4. Start automation. The worker selects only verified, low-risk buyers with current reviewed identity/import documents, a verification no older than 30 days, and a product-match score of at least 80. It respects product exclusions, suppressions, replies and the three-touch cadence with four-day spacing.
5. Product or sender changes invalidate authorization. Pausing a campaign or the installation is checked again immediately before transmission. In-progress SMTP requests may already have been accepted when a pause is clicked.

Campaigns use deterministic reviewed templates. Gemini cannot silently modify an authorized message. The worker binds each approval to the product, sender identity and template version. Changed message text is blocked at dispatch.

`OUTREACH_ENABLED=False` remains an independent installation-level stop. With sending disabled, an authorized campaign can prepare a bounded queue, but no message is sent or recorded as sent. Global hourly/daily limits and each campaign's daily limit are enforced at dispatch. No worker can override payment verification or confirm an order.

## Buyer feed

`BUYER_FEED_URL` is optional. When configured, the worker imports it once daily. It must be a public HTTPS URL, with no embedded username/password, and return an array of up to 500 records within 2 MB. Redirects are not followed. The feed is operator-selected; no endpoint is guessed. A record requires `company_name`, `country`, `product_category` and `source`; provenance should include a real `source_url` and supporting document reference. Scores and verification states from the feed are ignored. Imported records enter evidence review, and never become verified merely because a provider labeled them so. This adapter supports a normalized JSON feed; provider-specific authentication and formats require a separate connector.

Without a configured feed, job history reports **Not configured** and does not fabricate buyers. A failed import is reported in its job summary and retried on a later cycle. Validation checks all rows before ingestion; successful earlier inserts are deduplicated if a database interruption requires retrying a batch.

## Production

The Render blueprint now includes a separate paid background worker. Give web and worker the **same managed PostgreSQL DATABASE_URL**, exporter identity and sender settings. Generate a stable signing key and operator credentials. The worker has no public HTTP port. Do not use independent SQLite files for multiple processes on different hosts. Review the paid service configuration before deploying; nothing has been deployed or purchased by this local change.

Production connections still required: a genuine buyer source, a supported email transport, inbound mailbox/provider event integration, and real exporter details. Existing reply ingestion remains an authenticated operator API, not an unsigned public mailbox webhook. Until inbound events are connected, use manual reply ingestion; do not enable unattended outreach that depends on automatic reply detection.

Status and the last 20 runs are available in **Automation & campaigns**, or `GET /api/v1/automation/status`. State changes and manual runs require authentication and browser request protection. The UI shows feed configuration, sending enablement, heartbeat, campaign blocks, drafted/sent counts, review backlog and job failures. Job history is monitoring, not an external alert delivery system.
