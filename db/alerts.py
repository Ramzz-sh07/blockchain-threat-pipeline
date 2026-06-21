"""
Alert system: sends email notifications and persists an alert history
in MongoDB whenever a wallet is flagged above the risk threshold.
"""
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from dotenv import load_dotenv
load_dotenv()

from db.mongo import get_db

logger = logging.getLogger(__name__)

ALERT_EMAIL_FROM      = os.getenv("ALERT_EMAIL_FROM", "")
ALERT_EMAIL_PASSWORD  = os.getenv("ALERT_EMAIL_PASSWORD", "")
ALERT_EMAIL_TO        = os.getenv("ALERT_EMAIL_TO", "")
ALERT_RISK_THRESHOLD  = float(os.getenv("ALERT_RISK_THRESHOLD", "70"))

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def get_alerts_collection():
    return get_db()["alerts"]


def send_email_alert(wallet: str, category: str, score: float) -> bool:
    """Send an email alert for a flagged wallet. Returns True on success."""
    if not (ALERT_EMAIL_FROM and ALERT_EMAIL_PASSWORD and ALERT_EMAIL_TO):
        logger.warning("Email alert skipped — ALERT_EMAIL_* not configured in .env")
        return False

    subject = f"[ALERT] Suspicious wallet flagged — {category}"
    body = (
        f"A wallet has been flagged by the Blockchain Threat Detection Pipeline.\n\n"
        f"Wallet:    {wallet}\n"
        f"Category:  {category}\n"
        f"Risk score: {score:.1f}/100\n"
        f"Time:      {datetime.now(timezone.utc).isoformat()}\n"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = ALERT_EMAIL_FROM
    msg["To"] = ALERT_EMAIL_TO

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD)
            server.sendmail(ALERT_EMAIL_FROM, [ALERT_EMAIL_TO], msg.as_string())
        logger.info("Email alert sent for wallet %s", wallet)
        return True
    except Exception as exc:
        logger.error("Failed to send email alert: %s", exc)
        return False


def log_alert_history(wallet: str, category: str, score: float, email_sent: bool):
    """Persist the alert event to MongoDB's alerts collection."""
    collection = get_alerts_collection()
    collection.insert_one({
        "wallet": wallet,
        "category": category,
        "risk_score": score,
        "email_sent": email_sent,
        "timestamp": datetime.now(timezone.utc),
    })


def trigger_alert(wallet: str, category: str, score: float):
    """
    Main entry point: checks threshold, sends email, logs to alert history.
    Call this whenever a wallet is flagged.
    """
    if score < ALERT_RISK_THRESHOLD:
        return

    email_sent = send_email_alert(wallet, category, score)
    log_alert_history(wallet, category, score, email_sent)
    logger.warning(
        "ALERT TRIGGERED — wallet=%s category=%s score=%.1f email_sent=%s",
        wallet, category, score, email_sent
    )


def get_recent_alerts(limit: int = 50) -> list[dict]:
    """Fetch the most recent alerts for display in the dashboard."""
    collection = get_alerts_collection()
    cursor = collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return list(cursor)
