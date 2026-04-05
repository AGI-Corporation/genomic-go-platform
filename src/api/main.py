"""Genomic.go Platform — JSON-RPC 2.0 API with Bearer token authentication.

All endpoints speak JSON-RPC 2.0.  Requests without a valid
``Authorization: Bearer <token>`` header receive:

    {"jsonrpc": "2.0", "error": {"code": -32001,
     "message": "Unauthorized — Bearer token required"}, "id": null}

The expected token is read from the ``GENOMIC_API_TOKEN`` environment variable.
"""

import os
import logging
from typing import Any, Optional, Union

from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSON-RPC 2.0 data models
# ---------------------------------------------------------------------------

JSONRPC_VERSION = "2.0"

# Standard error codes (JSON-RPC 2.0 spec)
ERROR_PARSE_ERROR = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL = -32603

# Custom server error codes (-32000 to -32099)
ERROR_UNAUTHORIZED = -32001


class JsonRpcRequest(BaseModel):
    """Incoming JSON-RPC 2.0 request envelope."""

    jsonrpc: str
    method: str
    params: Optional[Union[dict, list]] = None
    id: Optional[Union[str, int]] = None

    @field_validator("jsonrpc")
    @classmethod
    def must_be_v2(cls, v: str) -> str:
        if v != JSONRPC_VERSION:
            raise ValueError("Only JSON-RPC 2.0 is supported")
        return v


def _error_response(
    code: int, message: str, request_id: Optional[Union[str, int]] = None
) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": JSONRPC_VERSION,
        "error": {"code": code, "message": message},
        "id": request_id,
    }


def _success_response(
    result: Any, request_id: Optional[Union[str, int]] = None
) -> dict:
    """Build a JSON-RPC 2.0 success response."""
    return {
        "jsonrpc": JSONRPC_VERSION,
        "result": result,
        "id": request_id,
    }


# ---------------------------------------------------------------------------
# Bearer token authentication helper
# ---------------------------------------------------------------------------

def _get_expected_token() -> str:
    """Return the Bearer token from the environment."""
    token = os.environ.get("GENOMIC_API_TOKEN", "")
    return token


def _authenticate(authorization: Optional[str]) -> bool:
    """Return True when the Authorization header carries a valid Bearer token."""
    expected = _get_expected_token()
    if not expected:
        # If no token is configured the platform is considered unprotected only
        # in development.  Log a warning so operators notice.
        logger.warning(
            "GENOMIC_API_TOKEN is not set — all requests will be rejected."
        )
        return False
    if not authorization:
        return False
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False
    return parts[1] == expected


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Genomic.go Platform API",
    description="JSON-RPC 2.0 API for the Genomic.go research platform.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Registered JSON-RPC method handlers
# ---------------------------------------------------------------------------

def _handle_platform_info(_params: Any) -> dict:
    """Return basic platform metadata."""
    return {
        "name": "Genomic.go Platform",
        "version": "1.0.0",
        "capabilities": [
            "compound_library",
            "clinical_trials",
            "genomics_analysis",
            "agent_orchestration",
        ],
    }


def _handle_compound_search(params: Any) -> dict:
    """Stub: delegate to CompoundSearcher (lazy import to keep API light)."""
    if not isinstance(params, dict):
        raise ValueError("params must be an object with a 'query' key")
    query = params.get("query")
    if not query:
        raise ValueError("'query' is required")

    # Lazy import so the API starts even without heavy ML dependencies installed.
    try:
        import sys, os as _os
        sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), ".."))
        from compound_library.compound_searcher import CompoundSearcher  # noqa: PLC0415

        searcher = CompoundSearcher()
        results = searcher.search(
            query=query,
            limit=params.get("limit", 10),
            filters=params.get("filters"),
        )
        return {"results": results}
    except Exception as exc:  # pragma: no cover
        logger.error("compound.search failed: %s", exc)
        raise RuntimeError(str(exc)) from exc


_METHOD_REGISTRY: dict[str, Any] = {
    "platform.info": _handle_platform_info,
    "compound.search": _handle_compound_search,
}


# ---------------------------------------------------------------------------
# Main JSON-RPC endpoint
# ---------------------------------------------------------------------------

@app.post("/rpc")
async def rpc_endpoint(
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> JSONResponse:
    """Single JSON-RPC 2.0 dispatch endpoint.

    Authentication is checked before the request body is parsed so that
    the JSON-RPC ``id`` is unknown at auth time — per the spec the id in
    the error response is ``null``.
    """
    # --- 1. Authenticate ---
    if not _authenticate(authorization):
        return JSONResponse(
            status_code=401,
            content=_error_response(
                ERROR_UNAUTHORIZED,
                "Unauthorized \u2014 Bearer token required",
            ),
        )

    # --- 2. Parse body ---
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=_error_response(ERROR_PARSE_ERROR, "Parse error"),
        )

    # --- 3. Validate JSON-RPC envelope ---
    try:
        rpc_req = JsonRpcRequest(**body)
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content=_error_response(
                ERROR_INVALID_REQUEST,
                f"Invalid Request: {exc}",
                body.get("id") if isinstance(body, dict) else None,
            ),
        )

    # --- 4. Dispatch method ---
    handler = _METHOD_REGISTRY.get(rpc_req.method)
    if handler is None:
        return JSONResponse(
            status_code=404,
            content=_error_response(
                ERROR_METHOD_NOT_FOUND,
                f"Method not found: {rpc_req.method}",
                rpc_req.id,
            ),
        )

    try:
        result = handler(rpc_req.params)
        return JSONResponse(content=_success_response(result, rpc_req.id))
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content=_error_response(ERROR_INVALID_PARAMS, str(exc), rpc_req.id),
        )
    except Exception as exc:
        logger.exception("Unhandled error in method %s", rpc_req.method)
        return JSONResponse(
            status_code=500,
            content=_error_response(ERROR_INTERNAL, "Internal error", rpc_req.id),
        )


# ---------------------------------------------------------------------------
# Health check (unauthenticated — used by load-balancers / probes)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    """Liveness probe — always returns 200."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )
