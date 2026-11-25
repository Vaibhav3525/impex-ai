"""
Day 11 — SMTP Email Dispatch & Deliverability Engine
PRD §6 & §10: Rate-limited email dispatch with Mode A human signoff validation,
automatic hard-bounce suppression, daily/hourly quota enforcement, and follow-up scheduling.
"""

from __future__ import annotations
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.models.lead import Lead
from app.models.outreach import OutreachEmail, SuppressionList


def get_send_window_metrics(db: Session) -> Dict[str, Any]:
    """
    Calculates dispatch count within the current rolling 1-hour and calendar day windows.
    Enforces DAILY_SEND_LIMIT and HOURLY_SEND_LIMIT from application settings.
    """
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    sent_today = (
        db.query(OutreachEmail)
        .filter(OutreachEmail.status.in_(["Sent", "Delivered", "Replied", "Sending", "Delivery Unknown"]))
        .filter(OutreachEmail.sent_at >= today_start)
        .count()
    )

    sent_this_hour = (
        db.query(OutreachEmail)
        .filter(OutreachEmail.status.in_(["Sent", "Delivered", "Replied", "Sending", "Delivery Unknown"]))
        .filter(OutreachEmail.sent_at >= one_hour_ago)
        .count()
    )

    daily_remaining = max(0, settings.DAILY_SEND_LIMIT - sent_today)
    hourly_remaining = max(0, settings.HOURLY_SEND_LIMIT - sent_this_hour)
    can_send = daily_remaining > 0 and hourly_remaining > 0

    return {
        "sent_today": sent_today,
        "sent_this_hour": sent_this_hour,
        "daily_limit": settings.DAILY_SEND_LIMIT,
        "hourly_limit": settings.HOURLY_SEND_LIMIT,
        "daily_remaining": daily_remaining,
        "hourly_remaining": hourly_remaining,
        "can_send": can_send,
    }


def is_suppressed(db, address):
    address = (address or "").lower().strip()
    domain = address.rsplit("@", 1)[-1]
    return db.query(SuppressionList).filter(SuppressionList.email.in_([address, domain, "@" + domain])).first()


def send_outreach_email(db: Session, email_id: str, bypass_rate_limits: bool = False) -> Dict[str, Any]:
    """Only a confirmed SMTP acceptance can create a Sent record. Never simulates delivery."""
    from sqlalchemy import update
    from app.models.dispatch_lock import DispatchLock
    import ssl
    email_obj = db.query(OutreachEmail).filter(OutreachEmail.email_id == email_id).first()
    def fail(message):
        return {"success": False, "error": message}
    if not email_obj:
        return fail("Email not found.")
    if email_obj.status != "Approved" or not email_obj.approved_by:
        return fail("Mode A Violation: authenticated operator approval is required.")
    if bypass_rate_limits:
        return fail("Rate limit bypass is disabled.")
    if not settings.OUTREACH_ENABLED:
        return fail("Email sending is disabled. Configure and enable outreach first.")
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD or not settings.SMTP_FROM_EMAIL:
        return fail("SMTP credentials and an explicit sender address are required. No email was sent.")
    now = datetime.now(timezone.utc)
    if email_obj.scheduled_for:
        due = email_obj.scheduled_for.replace(tzinfo=timezone.utc) if email_obj.scheduled_for.tzinfo is None else email_obj.scheduled_for
        if due > now:
            return fail("Email is not due yet.")
    # Serialize quota/claim across server workers using a database row lock.
    db.execute(update(DispatchLock).where(DispatchLock.id == 1).values(version=DispatchLock.version + 1))
    db.refresh(email_obj)
    if email_obj.status != "Approved":
        db.rollback()
        return fail("Email is already being dispatched or has changed state.")
    from app.services.automation_service import dispatch_permission
    policy_error = dispatch_permission(db, email_obj)
    if policy_error:
        db.rollback()
        return fail(policy_error)
    lead = db.query(Lead).filter(Lead.lead_id == email_obj.lead_id).first()
    if is_suppressed(db, email_obj.to_email):
        email_obj.status = "Suppressed"
        db.commit()
        return fail("Recipient is on the suppression list.")
    if not lead or lead.verification_status != "Verified" or lead.risk_level != "LOW" or lead.outreach_status in {"Replied", "Opted-Out", "Suppressed", "Bounced"}:
        db.rollback()
        return fail("Recipient is unverified, high risk, or their outreach has been halted.")
    sent = db.query(OutreachEmail).filter(OutreachEmail.lead_id == lead.lead_id, OutreachEmail.status.in_(["Sent", "Delivered", "Replied"])).all()
    if len(sent) >= 3 or any(e.sequence_step == email_obj.sequence_step for e in sent) or email_obj.sequence_step != len(sent) + 1:
        db.rollback()
        return fail("Cadence limit or sequence order would be violated.")
    if not get_send_window_metrics(db)["can_send"]:
        db.rollback()
        return fail("Dispatch rate limit reached.")
    email_obj.status = "Sending"
    email_obj.sent_at = now  # Reserve quota before network IO.
    db.commit()  # A worker crash leaves an unclaimable Sending record for investigation.
    msg = MIMEMultipart("alternative")
    msg["Subject"] = email_obj.subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = email_obj.to_email
    msg.attach(MIMEText(email_obj.body_text, "plain"))
    if email_obj.body_html:
        msg.attach(MIMEText(email_obj.body_html, "html"))
    try:
        context = ssl.create_default_context()
        if settings.SMTP_USE_SSL:
            server_ctx = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15, context=context)
        else:
            server_ctx = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        with server_ctx as server:
            if not settings.SMTP_USE_SSL:
                server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            refused = server.sendmail(settings.SMTP_FROM_EMAIL, [email_obj.to_email], msg.as_string())
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
    except smtplib.SMTPRecipientsRefused:
        email_obj.status = "Failed"
        email_obj.error_message = "SMTP recipient refused."
        if not is_suppressed(db, email_obj.to_email):
            db.add(SuppressionList(email=email_obj.to_email.lower().strip(), reason="Hard Bounce"))
        db.commit()
        return fail(email_obj.error_message)
    except Exception:
        # SMTP may have accepted DATA before a connection loss. Never retry automatically.
        email_obj.status = "Delivery Unknown"
        email_obj.error_message = "SMTP outcome is uncertain. Check provider logs before retrying."
        db.commit()
        return fail(email_obj.error_message)
    email_obj.status, email_obj.sent_at, email_obj.error_message = "Sent", now, None
    lead.outreach_status, lead.pipeline_stage = "Sent", "Email Sent"
    lead.next_followup = now + timedelta(days=4) if email_obj.sequence_step < 3 else None
    db.commit()
    return {"success": True, "email_id": email_obj.email_id, "to_email": email_obj.to_email, "status": "Sent", "sent_at": now.isoformat(), "message": "Accepted by SMTP server; delivery is not confirmed.", "lead_id": lead.lead_id}


def dispatch_approved_emails(
    db: Session,
    max_emails: Optional[int] = None,
    bypass_rate_limits: bool = False,
) -> Dict[str, Any]:
    """
    Batches and dispatches pending approved emails up to remaining hourly/daily quota.
    """
    metrics = get_send_window_metrics(db)
    if not bypass_rate_limits:
        available_quota = min(metrics["daily_remaining"], metrics["hourly_remaining"])
        if available_quota <= 0:
            return {
                "dispatched_count": 0,
                "errors": ["Rate limit reached. No remaining send capacity in current window."],
                "metrics": metrics,
            }
        limit = min(max_emails or available_quota, available_quota)
    else:
        limit = max_emails or 50

    approved_emails = (
        db.query(OutreachEmail)
        .filter(OutreachEmail.status == "Approved")
        .order_by(OutreachEmail.approved_at.asc())
        .limit(limit)
        .all()
    )

    dispatched = 0
    failures = []

    for em in approved_emails:
        res = send_outreach_email(db, em.email_id, bypass_rate_limits=bypass_rate_limits)
        if res.get("success"):
            dispatched += 1
        else:
            failures.append({em.email_id: res.get("error")})

    return {
        "dispatched_count": dispatched,
        "failed_count": len(failures),
        "failures": failures,
        "updated_metrics": get_send_window_metrics(db),
    }
