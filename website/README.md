# Science.Delivery — Marketing Website

Public-facing website for Science.Delivery: informative overview of the platform,
the 425-compound CRBN-targeted library, immersive molecular dynamics on RP1, and
research tooling — with a strong call to action and a detailed contact form that
forwards submissions to **agi@science.delivery**.

## Structure
- `index.html`, `styles.css`, `app.js` — the static single-page site (no build step).
- `backend/contact_api.py` — FastAPI app that serves the static site and exposes
  `POST /api/contact`, forwarding submissions by email to `agi@science.delivery`.

## Contact form behavior
- Client validates required fields and email format, then POSTs JSON to `/api/contact`.
- The backend emails `CONTACT_TO` (default `agi@science.delivery`) via SMTP.
- Every submission is also appended to `backend/submissions.jsonl` so nothing is lost.
- If SMTP is not configured, submissions are accepted and stored, and the response
  indicates delivery is pending email configuration — the site still works.

## Run locally
```bash
cd website/backend
pip install -r requirements.txt
uvicorn contact_api:app --port 8100
# open http://localhost:8100/
```

## Go live (enable email delivery)
Set these environment variables on the backend, then restart:
- `SMTP_HOST`, `SMTP_PORT` (587 STARTTLS or 465 SSL), `SMTP_USER`, `SMTP_PASS`
- `CONTACT_TO` (defaults to `agi@science.delivery`), `CONTACT_FROM`
- `CONTACT_CORS_ORIGINS` if the frontend is served from a different origin

Verified: with SMTP configured, submissions deliver to agi@science.delivery with
a descriptive subject and the sender's address as Reply-To.
