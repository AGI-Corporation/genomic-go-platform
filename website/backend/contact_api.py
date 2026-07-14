"""
Contact form backend for the Science.Delivery marketing site.

Receives contact submissions and forwards them by email to CONTACT_TO
(default agi@science.delivery). Uses SMTP configured via environment variables.
If SMTP is not configured, submissions are accepted, logged, and persisted to
a local JSONL file so nothing is lost, and the response indicates delivery is
pending email configuration.
"""
from __future__ import annotations

import json
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

CONTACT_TO = os.environ.get("CONTACT_TO", "agi@science.delivery")
CONTACT_FROM = os.environ.get("CONTACT_FROM", "website@science.delivery")
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
SMTP_STARTTLS = os.environ.get("SMTP_STARTTLS", "true").lower() != "false"
STORE = Path(os.environ.get("CONTACT_STORE", str(Path(__file__).parent / "submissions.jsonl")))
SITE_DIR = Path(__file__).resolve().parents[1]

app = FastAPI(title="Science.Delivery Contact API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CONTACT_CORS_ORIGINS", "*").split(","),
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class ContactMessage(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    organization: str | None = Field(default=None, max_length=200)
    interest: str | None = Field(default=None, max_length=100)
    message: str = Field(min_length=1, max_length=5000)


def _persist(payload: dict, delivered: bool) -> None:
    record = {"received_at": datetime.now(timezone.utc).isoformat(), "delivered": delivered, **payload}
    with STORE.open("a") as fh:
        fh.write(json.dumps(record) + "\n")


def _send_email(m: ContactMessage) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"[Science.Delivery] New inquiry from {m.name}"
    msg["From"] = CONTACT_FROM
    msg["To"] = CONTACT_TO
    msg["Reply-To"] = m.email
    body = (
        f"New contact form submission\n\n"
        f"Name:         {m.name}\n"
        f"Email:        {m.email}\n"
        f"Organization: {m.organization or '—'}\n"
        f"Interest:     {m.interest or '—'}\n\n"
        f"Message:\n{m.message}\n"
    )
    msg.set_content(body)

    context = ssl.create_default_context()
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as s:
            if SMTP_USER:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            if SMTP_STARTTLS:
                s.starttls(context=context)
            if SMTP_USER:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)


@app.get("/api/health")
def health():
    return {"status": "ok", "email_configured": bool(SMTP_HOST), "to": CONTACT_TO}


@app.post("/api/contact")
def contact(m: ContactMessage):
    payload = m.model_dump()
    if not SMTP_HOST:
        _persist(payload, delivered=False)
        return {
            "status": "accepted",
            "delivered": False,
            "detail": "Received. Email delivery is pending SMTP configuration.",
        }
    try:
        _send_email(m)
    except Exception as exc:  # noqa: BLE001
        _persist(payload, delivered=False)
        raise HTTPException(status_code=502, detail=f"Email delivery failed: {exc}") from exc
    _persist(payload, delivered=True)
    return {"status": "sent", "delivered": True, "to": CONTACT_TO}


# Serve the static site from the parent directory (index.html, styles.css, app.js).
app.mount("/", StaticFiles(directory=str(SITE_DIR), html=True), name="site")
