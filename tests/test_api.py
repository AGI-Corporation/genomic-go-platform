"""Tests for the Genomic.go Platform JSON-RPC 2.0 API with Bearer token auth."""

import os
import sys
import types
import pytest
from unittest.mock import patch

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi.testclient import TestClient  # noqa: E402

# Provide a known token before the app module is imported so env is set.
_TEST_TOKEN = "test-secret-token"

os.environ["GENOMIC_API_TOKEN"] = _TEST_TOKEN

from api.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(token: str = _TEST_TOKEN) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _rpc_body(method: str, params=None, rpc_id=1) -> dict:
    body = {"jsonrpc": "2.0", "method": method, "id": rpc_id}
    if params is not None:
        body["params"] = params
    return body


# ---------------------------------------------------------------------------
# Health endpoint (no auth required)
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Authentication — missing / invalid token
# ---------------------------------------------------------------------------

class TestBearerTokenAuthentication:
    """Verify the JSON-RPC 2.0 unauthorized error is returned correctly."""

    def test_missing_authorization_header(self):
        """No Authorization header → 401 with JSON-RPC error -32001."""
        response = client.post("/rpc", json=_rpc_body("platform.info"))
        assert response.status_code == 401
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["error"]["code"] == -32001
        assert "Unauthorized" in data["error"]["message"]
        assert "Bearer token required" in data["error"]["message"]
        assert data["id"] is None

    def test_wrong_token_returns_401(self):
        """Wrong bearer token → 401."""
        response = client.post(
            "/rpc",
            json=_rpc_body("platform.info"),
            headers=_auth_headers("wrong-token"),
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == -32001
        assert data["id"] is None

    def test_malformed_authorization_scheme(self):
        """Basic auth instead of Bearer → 401."""
        response = client.post(
            "/rpc",
            json=_rpc_body("platform.info"),
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == -32001

    def test_empty_token_returns_401(self):
        """Empty token value → 401."""
        response = client.post(
            "/rpc",
            json=_rpc_body("platform.info"),
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401

    def test_valid_token_passes_auth(self):
        """Valid bearer token allows the request through."""
        response = client.post(
            "/rpc",
            json=_rpc_body("platform.info"),
            headers=_auth_headers(),
        )
        # Should not be 401
        assert response.status_code == 200
        data = response.json()
        assert "error" not in data
        assert data["jsonrpc"] == "2.0"

    def test_no_token_configured_rejects_all(self):
        """When GENOMIC_API_TOKEN is unset every request is rejected."""
        with patch.dict(os.environ, {"GENOMIC_API_TOKEN": ""}):
            response = client.post(
                "/rpc",
                json=_rpc_body("platform.info"),
                headers=_auth_headers("any-token"),
            )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == -32001


# ---------------------------------------------------------------------------
# JSON-RPC protocol validation (authenticated requests)
# ---------------------------------------------------------------------------

class TestJsonRpcProtocol:
    """Verify JSON-RPC 2.0 envelope handling."""

    def test_invalid_jsonrpc_version(self):
        response = client.post(
            "/rpc",
            json={"jsonrpc": "1.0", "method": "platform.info", "id": 1},
            headers=_auth_headers(),
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == -32600  # Invalid Request

    def test_method_not_found(self):
        response = client.post(
            "/rpc",
            json=_rpc_body("nonexistent.method"),
            headers=_auth_headers(),
        )
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == -32601
        assert data["id"] == 1

    def test_parse_error_on_invalid_json(self):
        response = client.post(
            "/rpc",
            content=b"not json {{{",
            headers={**_auth_headers(), "Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == -32700

    def test_notification_id_is_null(self):
        """JSON-RPC notifications have no id; response id must also be null."""
        response = client.post(
            "/rpc",
            json={"jsonrpc": "2.0", "method": "platform.info"},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["id"] is None

    def test_id_preserved_in_response(self):
        response = client.post(
            "/rpc",
            json=_rpc_body("platform.info", rpc_id=42),
            headers=_auth_headers(),
        )
        assert response.json()["id"] == 42

    def test_string_id_preserved(self):
        response = client.post(
            "/rpc",
            json=_rpc_body("platform.info", rpc_id="req-abc"),
            headers=_auth_headers(),
        )
        assert response.json()["id"] == "req-abc"


# ---------------------------------------------------------------------------
# platform.info method
# ---------------------------------------------------------------------------

class TestPlatformInfoMethod:
    def test_returns_platform_name(self):
        response = client.post(
            "/rpc",
            json=_rpc_body("platform.info"),
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["name"] == "Genomic.go Platform"
        assert "compound_library" in result["capabilities"]

    def test_result_structure(self):
        response = client.post(
            "/rpc",
            json=_rpc_body("platform.info"),
            headers=_auth_headers(),
        )
        result = response.json()["result"]
        assert "version" in result
        assert "capabilities" in result
        assert isinstance(result["capabilities"], list)


# ---------------------------------------------------------------------------
# compound.search method
# ---------------------------------------------------------------------------

class TestCompoundSearchMethod:
    """Tests for the compound.search JSON-RPC method (CompoundSearcher mocked)."""

    def _mock_searcher(self, results=None):
        """Context manager that patches CompoundSearcher.search."""
        if results is None:
            results = [{"id": "CMP-001", "name": "Aspirin", "score": 0.95}]
        mock_instance = type(
            "MockSearcher", (), {"search": lambda self, **kw: results}
        )()
        return patch(
            "compound_library.compound_searcher.CompoundSearcher",
            return_value=mock_instance,
        )

    def test_missing_query_returns_invalid_params(self):
        response = client.post(
            "/rpc",
            json=_rpc_body("compound.search", params={}),
            headers=_auth_headers(),
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == -32602  # Invalid params

    def test_non_dict_params_returns_invalid_params(self):
        response = client.post(
            "/rpc",
            json=_rpc_body("compound.search", params=["bad"]),
            headers=_auth_headers(),
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == -32602

    def test_successful_search_returns_results(self):
        """Valid query with mocked CompoundSearcher returns result list."""
        mock_results = [{"id": "CMP-001", "name": "Aspirin", "score": 0.95}]

        class MockSearcher:
            def search(self, **kw):
                return mock_results

        fake_mod = types.ModuleType("compound_library.compound_searcher")
        fake_mod.CompoundSearcher = MockSearcher

        original = sys.modules.get("compound_library.compound_searcher")
        sys.modules["compound_library.compound_searcher"] = fake_mod
        try:
            response = client.post(
                "/rpc",
                json=_rpc_body("compound.search", params={"query": "antiviral"}),
                headers=_auth_headers(),
            )
        finally:
            if original is None:
                sys.modules.pop("compound_library.compound_searcher", None)
            else:
                sys.modules["compound_library.compound_searcher"] = original

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "results" in data["result"]
        assert data["result"]["results"] == mock_results
