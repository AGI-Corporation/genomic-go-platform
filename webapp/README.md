# AGI Compound Library — Web App

A secured web application for browsing the AGI synthetic compound library (425
compounds targeting CRBN for pro-apoptotic activity in cancer). Built on the
Genomic.go platform.

## Features

- **Login-gated access** — JWT auth; no data is served without a valid session.
- **Compound browser** — searchable, filterable, sortable table of all 425 compounds
  (ID, SMILES, substituent, molecular weight, LogP, ΔG binding, IC50, goodness score).
- **Filters & facets** — filter by substituent and max IC50; live substituent counts.
- **Detail pages** — full properties with a rendered 2D molecular structure (from SMILES).
- **Semantic search** — `/api/search` uses the existing Qdrant `CompoundSearcher`
  when `QDRANT_URL` is configured, and degrades to substring search otherwise.

## Data

`data/compounds.json` (also mirrored to `webapp/backend/compounds.json`) holds all
425 compounds, extracted from the source AGI compound PDFs. Fields: `compound_id`,
`smiles`, `substituent`, `molecular_weight`, `logp`, `binding_dg_kcal_mol`,
`ic50_um`, `goodness_score`, plus `target_protein`, `mechanism`, `therapeutic_area`.

Two compounds (AGI-011, AGI-020) lack molecular weight in the source PDFs; six
compounds with garbled SMILES in the detail source were corrected from the
table-of-contents source.

## Run locally

### Backend (FastAPI)
```bash
cd webapp/backend
pip install -r requirements.txt
uvicorn main:app --port 8000
```

Environment:
- `APP_SECRET_KEY` — JWT signing key (set a real secret in production).
- `APP_DEFAULT_PASSWORD` — default `researcher` password (change it).
- `APP_USERS_JSON` — optional JSON map of `{username: bcrypt_hash}` for multiple users.
- `QDRANT_URL` / `QDRANT_API_KEY` / `QDRANT_COLLECTION` — enable semantic search.

### Frontend (Vite + React)
```bash
cd webapp/frontend
npm install
npm run dev        # dev server, proxies /api to :8000
npm run build      # production build to dist/
```

## Notes

- Default credentials are for local development only. Set `APP_SECRET_KEY` and
  real users before any shared or production deployment.
- The frontend is a single-page app; serve `dist/` behind any static host with
  `/api/*` proxied to the backend.
