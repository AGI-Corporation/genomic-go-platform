"""
AGI Compound Library — FastAPI backend.

Serves the 425-compound AGI synthetic library with search, filter, sort, and
detail endpoints, behind a lightweight JWT login. Semantic search delegates to
the existing Qdrant-backed CompoundSearcher when configured, and falls back to
substring search over local data otherwise.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel

DATA_FILE = Path(__file__).parent / "compounds.json"
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "dev-only-change-me")
ALGORITHM = "HS256"
TOKEN_TTL_MIN = int(os.environ.get("APP_TOKEN_TTL_MIN", "720"))

# Single shared credential for the secured area. Override in production via env.
# Password default is "compound-access"; store a real bcrypt hash in APP_USERS_JSON.
def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _verify(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


_DEFAULT_USERS = {"researcher": _hash(os.environ.get("APP_DEFAULT_PASSWORD", "compound-access"))}


def _load_users() -> dict[str, str]:
    raw = os.environ.get("APP_USERS_JSON")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return _DEFAULT_USERS


USERS = _load_users()

with DATA_FILE.open() as fh:
    COMPOUNDS: list[dict] = json.load(fh)
BY_ID = {c["compound_id"]: c for c in COMPOUNDS}

app = FastAPI(title="AGI Compound Library API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("APP_CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _make_token(sub: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_TTL_MIN)
    return jwt.encode({"sub": sub, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def current_user(token: str = Depends(oauth2_scheme)) -> str:
    cred_err = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise cred_err
        return sub
    except JWTError:
        raise cred_err


@app.post("/api/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends()):
    hashed = USERS.get(form.username)
    if not hashed or not _verify(form.password, hashed):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return Token(access_token=_make_token(form.username))


@app.get("/api/health")
def health():
    return {"status": "ok", "compounds": len(COMPOUNDS)}


def _matches(c: dict, q: str) -> bool:
    q = q.lower()
    return (
        q in c["compound_id"].lower()
        or q in (c.get("smiles") or "").lower()
        or q in (c.get("substituent") or "").lower()
        or q in (c.get("description") or "").lower()
    )


@app.get("/api/compounds")
def list_compounds(
    _user: str = Depends(current_user),
    q: Optional[str] = None,
    substituent: Optional[str] = None,
    mw_min: Optional[float] = None,
    mw_max: Optional[float] = None,
    ic50_max: Optional[float] = None,
    sort: str = Query("compound_id"),
    order: str = Query("asc"),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
):
    rows = COMPOUNDS
    if q:
        rows = [c for c in rows if _matches(c, q)]
    if substituent:
        rows = [c for c in rows if (c.get("substituent") or "") == substituent]
    if mw_min is not None:
        rows = [c for c in rows if (c.get("molecular_weight") or 0) >= mw_min]
    if mw_max is not None:
        rows = [c for c in rows if (c.get("molecular_weight") or 1e9) <= mw_max]
    if ic50_max is not None:
        rows = [c for c in rows if (c.get("ic50_um") is not None and c["ic50_um"] <= ic50_max)]

    reverse = order == "desc"
    rows = sorted(rows, key=lambda c: (c.get(sort) is None, c.get(sort)), reverse=reverse)
    total = len(rows)
    page = rows[offset : offset + limit]
    return {"total": total, "limit": limit, "offset": offset, "results": page}


@app.get("/api/compounds/facets")
def facets(_user: str = Depends(current_user)):
    subs: dict[str, int] = {}
    for c in COMPOUNDS:
        s = c.get("substituent") or "—"
        subs[s] = subs.get(s, 0) + 1
    mws = [c["molecular_weight"] for c in COMPOUNDS if c.get("molecular_weight")]
    ic50s = [c["ic50_um"] for c in COMPOUNDS if c.get("ic50_um") is not None]
    return {
        "count": len(COMPOUNDS),
        "substituents": sorted(subs.items(), key=lambda kv: -kv[1]),
        "mw_range": [min(mws), max(mws)] if mws else [0, 0],
        "ic50_range": [min(ic50s), max(ic50s)] if ic50s else [0, 0],
    }


@app.get("/api/compounds/{compound_id}")
def get_compound(compound_id: str, _user: str = Depends(current_user)):
    c = BY_ID.get(compound_id)
    if not c:
        raise HTTPException(status_code=404, detail="Compound not found")
    return c


@app.get("/api/search")
def semantic_search(
    query: str,
    _user: str = Depends(current_user),
    limit: int = Query(10, le=50),
):
    """Semantic search via Qdrant CompoundSearcher when configured; else substring."""
    qdrant_url = os.environ.get("QDRANT_URL")
    if qdrant_url:
        try:
            import sys

            sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))
            from compound_library.compound_searcher import CompoundSearcher

            searcher = CompoundSearcher(
                collection_name=os.environ.get("QDRANT_COLLECTION", "compounds"),
                qdrant_url=qdrant_url,
                qdrant_api_key=os.environ.get("QDRANT_API_KEY"),
            )
            return {"mode": "semantic", "results": searcher.search(query, limit=limit)}
        except Exception as exc:  # noqa: BLE001 - degrade gracefully to substring
            fallback = [c for c in COMPOUNDS if _matches(c, query)][:limit]
            return {"mode": "fallback", "error": str(exc), "results": fallback}
    fallback = [c for c in COMPOUNDS if _matches(c, query)][:limit]
    return {"mode": "substring", "results": fallback}
