"""
shared/notifier.py — Notification helper for the SEO_LEAD platform.

Sends summary notifications via Email (SMTP) or Slack based on .env settings.

Usage:
    from shared.notifier import send_notification
    send_notification(
        subject="Keyword Research Complete",
        body="Found 42 keyword opportunities. Top: 'best crm software' (score 9)."
    )
"""

import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from shared.config import settings
from shared.logger import get_logger

log = get_logger("notifier")


def send_notification(subject: str, body: str) -> bool:
    """
    Send a notification using the method configured in .env.

    Returns True if sent successfully, False otherwise.
    """
    method = settings.notification_method.lower()

    if method == "none" or settings.dry_run:
        log.info("[%s] Notification skipped — subject: %s",
                 "DRY-RUN" if settings.dry_run else "DISABLED", subject)
        log.info("Body preview: %s", body[:200])
        return True

    if method == "email":
        return _send_email(subject, body)
    elif method == "slack":
        return _send_slack(subject, body)
    else:
        log.warning("Unknown notification method '%s'. Use email | slack | none.", method)
        return False


# ── Email via SMTP ───────────────────────────────────────────────────────────

def _send_email(subject: str, body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[SEO_LEAD] {subject}"
        msg["From"] = settings.smtp_user
        msg["To"] = settings.notification_to

        # Plain text part
        msg.attach(MIMEText(body, "plain"))

        # HTML part (simple formatting)
        html_body = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #2563eb;">[SEO_LEAD] {subject}</h2>
            <pre style="background: #f1f5f9; padding: 16px; border-radius: 8px;
                        font-size: 14px; line-height: 1.6;">{body}</pre>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="color: #94a3b8; font-size: 12px;">
                Sent by SEO_LEAD Automation Platform
            </p>
        </div>
        """
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        log.info("Email sent to %s — %s", settings.notification_to, subject)
        return True

    except Exception as exc:
        log.error("Failed to send email: %s", exc)
        return False


# ── Slack via Incoming Webhook ───────────────────────────────────────────────

def _send_slack(subject: str, body: str) -> bool:
    if not settings.slack_webhook_url:
        log.warning("SLACK_WEBHOOK_URL is empty — cannot send Slack notification")
        return False

    try:
        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"[SEO_LEAD] {subject}"},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"```{body}```"},
                },
            ]
        }

        resp = requests.post(
            settings.slack_webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        log.info("Slack notification sent — %s", subject)
        return True

    except Exception as exc:
        log.error("Failed to send Slack notification: %s", exc)
        return False
