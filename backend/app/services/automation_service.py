"""Bounded, restart-safe automation with explicit campaign authorization."""
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, update
from app.core.config import settings
from app.models.automation import AutomationPolicy, AutomationState, AutomationRun
from app.models.outreach import OutreachCampaign, OutreachEmail
from app.models.lead import Lead
from app.models.product_profile import ProductProfile
from app.services.evidence_service import current_evidence
from app.services.smtp_service import is_suppressed, send_outreach_email
from app.services.email_composer import compose_grounded_email
from app.services.followup_service import generate_next_followup_email
from app.services.qualification_service import calculate_qualification_score

def utcnow():
    return datetime.now(timezone.utc)

def aware(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value

def product_hash(product):
    data = {column.name: getattr(product, column.name) for column in ProductProfile.__table__.columns if column.name not in {"id", "created_at", "updated_at"}}
    data["template_version"] = 1
    data["exporter_name"] = settings.EXPORTER_NAME
    data["sender"] = settings.SMTP_FROM_EMAIL
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

def policy_problem(db, policy):
    if policy.status != "Active" or not policy.authorized_by or not policy.expires_at or aware(policy.expires_at) <= utcnow():
        return "Campaign is paused, unauthorized or expired."
    product = db.query(ProductProfile).filter_by(profile_id=policy.product_id).first()
    if not product or not product.is_active or not product.export_readiness:
        return "Product requires review."
    if product_hash(product) != policy.product_snapshot:
        return "Product changed after authorization. Review and authorize the campaign again."
    return None

def eligible(db, lead, product, policy):
    if lead.country.casefold() not in {c.casefold() for c in policy.countries}:
        return False
    if lead.verification_status != "Verified" or lead.risk_level != "LOW" or lead.outreach_status in {"Replied", "Opted-Out", "Suppressed", "Bounced"}:
        return False
    if not lead.business_email or is_suppressed(db, lead.business_email):
        return False
    evidence = current_evidence(db, lead.lead_id)
    if not {"identity", "imports"}.issubset(evidence) or not lead.last_verified or utcnow() - aware(lead.last_verified) > timedelta(days=30):
        return False
    match = calculate_qualification_score(lead, product)
    return not match.is_disqualified and match.qualification_score >= 80

def dispatch_permission(db, email):
    """Rechecked immediately before transmission, including campaign pauses."""
    policy = db.query(AutomationPolicy).filter_by(campaign_id=email.campaign_id).first()
    if not policy:
        return None if email.approval_mode != "Campaign" else "Campaign authorization is missing."
    state = db.get(AutomationState, 1)
    if not state or not state.enabled:
        return "Automation is paused."
    problem = policy_problem(db, policy)
    if problem:
        return problem
    product = db.query(ProductProfile).filter_by(profile_id=policy.product_id).one()
    lead = db.query(Lead).filter_by(lead_id=email.lead_id).first()
    if not lead or not eligible(db, lead, product, policy):
        return "Buyer no longer meets the campaign requirements."
    # The authorized composer owns the entire message; queued edits invalidate approval.
    draft = compose_grounded_email(lead, product, email.sequence_step, use_ai=False)
    if email.product_id != product.profile_id or email.subject != draft["subject"] or email.body_text != draft["body_text"]:
        return "Draft changed or no longer matches the authorized product/template."
    day = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    reserved = db.query(OutreachEmail).filter(OutreachEmail.campaign_id == policy.campaign_id, OutreachEmail.status.in_(["Sent", "Delivered", "Replied", "Sending", "Delivery Unknown"]), OutreachEmail.sent_at >= day).count()
    return "Campaign daily limit reached." if reserved >= policy.daily_limit else None

def import_feed(db):
    """Opt-in HTTPS JSON feed; external data remains unverified until reviewed."""
    import httpx
    import ipaddress
    import socket
    from urllib.parse import urlsplit
    from app.schemas.lead import LeadCreate
    from app.services.lead_service import ingest_lead
    if not settings.BUYER_FEED_URL:
        return {"status": "Not configured", "created": 0}
    url = urlsplit(settings.BUYER_FEED_URL)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.port not in {None, 443}:
        raise ValueError("Buyer feed requires a public HTTPS URL without embedded credentials.")
    addresses = socket.getaddrinfo(url.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Buyer feed must resolve to public addresses.")
    # No redirects, cookies or inherited proxy credentials. Bound both size and rows.
    with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client:
        with client.stream("GET", settings.BUYER_FEED_URL) as response:
            response.raise_for_status()
            raw = bytearray()
            for chunk in response.iter_bytes():
                raw.extend(chunk)
                if len(raw) > 2_000_000:
                    raise ValueError("Buyer feed exceeds the 2MB limit.")
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) > 500:
        raise ValueError("Buyer feed must be a JSON array of at most 500 records.")
    # Validate all rows before writing anything. Ignore external scores and statuses.
    rows = [LeadCreate.model_validate(row) for row in data]
    created = sum(int(ingest_lead(db, row)[1]) for row in rows)
    return {"status": "Imported for review", "created": created, "records": len(rows)}

def run_cycle(db, force=False):
    now, owner = utcnow(), uuid.uuid4().hex
    state = db.get(AutomationState, 1)
    if not state or not state.enabled:
        return {"status": "Paused"}
    if not force and state.last_cycle_at and now - aware(state.last_cycle_at) < timedelta(seconds=settings.AUTOMATION_INTERVAL_SECONDS):
        return {"status": "Not due"}
    claim = update(AutomationState).where(AutomationState.id == 1, AutomationState.enabled.is_(True), or_(AutomationState.lease_until.is_(None), AutomationState.lease_until < now))
    if not force:
        claim = claim.where(or_(AutomationState.last_cycle_at.is_(None), AutomationState.last_cycle_at <= now - timedelta(seconds=settings.AUTOMATION_INTERVAL_SECONDS)))
    claimed = db.execute(claim.values(lease_owner=owner, lease_until=now + timedelta(minutes=10), heartbeat_at=now).execution_options(synchronize_session=False))
    db.commit()
    if claimed.rowcount != 1:
        return {"status": "Already running"}
    run = AutomationRun(summary={})
    db.add(run); db.commit()
    summary = {"drafted": 0, "sent": 0, "needs_review": 0, "blocked_campaigns": [], "sending_enabled": settings.OUTREACH_ENABLED}
    try:
        # Mark abandoned runs for operator attention; Sending emails are never retried.
        db.query(AutomationRun).filter(AutomationRun.id != run.id, AutomationRun.status == "Running").update({"status": "Interrupted", "finished_at": now})
        db.commit()
        state = db.get(AutomationState, 1)
        if not state.last_import_at or now - aware(state.last_import_at) >= timedelta(days=1):
            try:
                summary["feed"] = import_feed(db)
                state.last_import_at = now
                db.commit()
            except Exception:
                db.rollback()
                summary["feed"] = {"status": "Failed", "error": "Buyer feed failed validation or could not be reached. Check configuration."}
        remaining, send_attempts = 10, 10
        for policy in db.query(AutomationPolicy).filter_by(status="Active").order_by(AutomationPolicy.id).all():
            if remaining <= 0:
                break
            problem = policy_problem(db, policy)
            if problem:
                summary["blocked_campaigns"].append({"id": policy.id, "reason": problem})
                continue
            product = db.query(ProductProfile).filter_by(profile_id=policy.product_id).one()
            candidates = db.query(Lead).filter(Lead.verification_status == "Verified", Lead.risk_level == "LOW").order_by(Lead.id).all()
            for lead in candidates:
                if remaining <= 0:
                    break
                day = now.replace(hour=0, minute=0, second=0, microsecond=0)
                reserved = db.query(OutreachEmail).filter(OutreachEmail.campaign_id == policy.campaign_id, or_(OutreachEmail.status.in_(["Queued", "Approved"]), (OutreachEmail.status.in_(["Sent", "Delivered", "Replied", "Sending", "Delivery Unknown"]) & (OutreachEmail.sent_at >= day)))).count()
                if reserved >= policy.daily_limit:
                    break
                if not eligible(db, lead, product, policy):
                    continue
                history = db.query(OutreachEmail).filter_by(lead_id=lead.lead_id).all()
                # Other campaigns, uncertain transmission and active human review win.
                if any(e.status in {"Queued", "Approved", "Sending", "Delivery Unknown"} for e in history):
                    continue
                sent = [e for e in history if e.status in {"Sent", "Delivered", "Replied"}]
                if sent:
                    if any(e.campaign_id != policy.campaign_id for e in sent):
                        continue
                    email = generate_next_followup_email(db, lead.lead_id, use_ai=False)
                    if not email:
                        continue
                else:
                    draft = compose_grounded_email(lead, product, use_ai=False)
                    email = OutreachEmail(campaign_id=policy.campaign_id, lead_id=lead.lead_id, product_id=product.profile_id, to_email=lead.business_email, to_name=lead.contact_name, company_name=lead.company_name, country=lead.country, subject=draft["subject"], body_text=draft["body_text"], body_html=draft["body_html"], grounding_evidence=draft["grounding_evidence"], sequence_step=1)
                    db.add(email)
                email.campaign_id = policy.campaign_id
                email.status, email.approval_mode = "Approved", "Campaign"
                email.approved_by, email.approved_at = "campaign:" + policy.authorized_by, now
                db.commit()
                summary["drafted"] += 1
                remaining -= 1
            if settings.OUTREACH_ENABLED:
                pending = db.query(OutreachEmail).filter_by(campaign_id=policy.campaign_id, status="Approved").order_by(OutreachEmail.id).limit(10).all()
                for email in pending:
                    if send_attempts <= 0:
                        break
                    send_attempts -= 1
                    result = send_outreach_email(db, email.email_id)
                    if result["success"]:
                        summary["sent"] += 1
        summary["needs_review"] = db.query(Lead).filter(Lead.verification_status.in_(["Unverified", "Partially Verified"])).count()
        run.status = "Completed"
    except Exception:
        db.rollback()
        run = db.get(AutomationRun, run.id)
        run.status, run.error = "Failed", "Automation cycle failed. Review server logs and configuration before retrying."
    finally:
        run.summary, run.finished_at = summary, utcnow()
        state = db.get(AutomationState, 1)
        if state.lease_owner == owner:
            state.lease_owner, state.lease_until = None, None
            state.last_cycle_at, state.heartbeat_at = now, utcnow()
        db.commit()
    return {"status": run.status, "run_id": run.id, **summary}
