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
        .filter(OutreachEmail.status == "Sent")
        .filter(OutreachEmail.sent_at >= today_start)
        .count()
    )

    sent_this_hour = (
        db.query(OutreachEmail)
        .filter(OutreachEmail.status == "Sent")
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


def send_outreach_email(
    db: Session,
    email_id: str,
    bypass_rate_limits: bool = False,
) -> Dict[str, Any]:
    """
    Dispatches a single approved outreach email.
    
    Invariants Enforced:
      1. Mode A Gate: Cannot send emails in 'Queued', 'Rejected', or 'Suppressed' state.
      2. Suppression Check: Never dispatches to an address on the suppression list.
      3. Rate Limiting: Respects hourly & daily volume caps to protect domain reputation.
      4. CRM Synchrony: Advances Lead to 'Email Sent' and schedules next follow-up (+4 days).
    """
    email_obj = db.query(OutreachEmail).filter(OutreachEmail.email_id == email_id).first()
    if not email_obj:
        return {"success": False, "error": f"Email '{email_id}' not found"}

    # 1. Gate: Mode A Human Signoff
    if email_obj.status != "Approved":
        return {
            "success": False,
            "error": f"Mode A Violation: Email has status '{email_obj.status}'. Only 'Approved' emails can be dispatched."
        }

    # 2. Gate: Suppression List Check
    norm_to_email = email_obj.to_email.lower().strip()
    suppressed = db.query(SuppressionList).filter(SuppressionList.email == norm_to_email).first()
    if suppressed:
        email_obj.status = "Suppressed"
        email_obj.error_message = f"Recipient is on suppression list: {suppressed.reason}"
        db.commit()
        return {
            "success": False,
            "error": f"Email '{norm_to_email}' is on suppression list ({suppressed.reason}). Dispatch blocked."
        }

    # 3. Gate: Rate Limiting
    if not bypass_rate_limits:
        metrics = get_send_window_metrics(db)
        if not metrics["can_send"]:
            return {
                "success": False,
                "error": f"Dispatch rate limit reached (Sent today: {metrics['sent_today']}/{metrics['daily_limit']}, Sent hour: {metrics['sent_this_hour']}/{metrics['hourly_limit']})"
            }

    # 4. Transmission (Real SMTP or Mock Dispatch)
    dispatch_success = False
    delivery_msg = ""

    from_addr = settings.SMTP_FROM_EMAIL or f"exports@{settings.SMTP_HOST.replace('smtp.', '')}"
    from_name = settings.SMTP_FROM_NAME or "Indian Export Corporation"

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = email_obj.subject
            msg["From"] = f"{from_name} <{from_addr}>"
            msg["To"] = email_obj.to_email

            part1 = MIMEText(email_obj.body_text, "plain")
            msg.attach(part1)
            if email_obj.body_html:
                part2 = MIMEText(email_obj.body_html, "html")
                msg.attach(part2)

            if settings.SMTP_USE_SSL:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15.0) as server:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(from_addr, [email_obj.to_email], msg.as_string())
            else:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15.0) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(from_addr, [email_obj.to_email], msg.as_string())

            dispatch_success = True
            delivery_msg = f"Dispatched via {settings.SMTP_HOST} SSL"

        except smtplib.SMTPRecipientsRefused as e:
            # Permanent bounce -> auto-suppress
            email_obj.status = "Failed"
            email_obj.error_message = f"Hard bounce / Recipient refused: {e}"
            supp = SuppressionList(
                email=norm_to_email,
                reason="Hard Bounce",
                notes=f"Auto-suppressed following SMTP recipient refusal on {email_obj.email_id}"
            )
            db.add(supp)
            db.commit()
            return {"success": False, "error": f"Recipient refused: {e}. Added to suppression list."}

        except Exception as exc:
            email_obj.status = "Failed"
            email_obj.error_message = f"SMTP transmission error: {str(exc)[:200]}"
            db.commit()
            return {"success": False, "error": email_obj.error_message}

    else:
        # Mock / Development mode dispatch simulation
        dispatch_success = True
        delivery_msg = f"[MOCK DISPATCH] Simulated delivery to {email_obj.to_email} (SMTP credentials not set)"

    # 5. Success State Update
    if dispatch_success:
        now_ts = datetime.now(timezone.utc)
        email_obj.status = "Sent"
        email_obj.sent_at = now_ts
        email_obj.error_message = None

        # Synchronize associated Lead in CRM
        lead = db.query(Lead).filter(Lead.lead_id == email_obj.lead_id).first()
        if lead:
            lead.outreach_status = "Sent"
            lead.pipeline_stage = "Email Sent"
            # Schedule next follow-up in 4 calendar days (PRD standard interval)
            lead.next_followup = now_ts + timedelta(days=4)
            ts_str = now_ts.strftime("%Y-%m-%d %H:%M:%S UTC")
            log_note = f"[Outreach Dispatched at {ts_str}]: Seq {email_obj.sequence_step} sent to {email_obj.to_email}. Next follow-up scheduled for {(now_ts + timedelta(days=4)).strftime('%Y-%m-%d')}."
            if lead.notes:
                lead.notes = f"{lead.notes}\n{log_note}"
            else:
                lead.notes = log_note

        db.commit()
        db.refresh(email_obj)

        return {
            "success": True,
            "email_id": email_obj.email_id,
            "to_email": email_obj.to_email,
            "status": "Sent",
            "sent_at": now_ts.isoformat(),
            "message": delivery_msg,
            "lead_id": email_obj.lead_id,
        }


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
