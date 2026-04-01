"""Tests for FastAPI REST API endpoints."""

import sys
import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_body(self):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


# ---------------------------------------------------------------------------
# Compound Search
# ---------------------------------------------------------------------------


class TestCompoundSearch:
    def _mock_searcher(self):
        mock = MagicMock()
        mock.search.return_value = [
            {
                "compound_id": "CHEMBL1",
                "name": "Imatinib",
                "similarity_score": 0.92,
            }
        ]
        return mock

    def test_search_returns_results(self):
        with patch(
            "compound_library.compound_searcher.CompoundSearcher",
            return_value=self._mock_searcher(),
        ):
            response = client.post(
                "/v1/compounds/search",
                json={"query": "kinase inhibitor for cancer", "limit": 5},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1
        assert data["compounds"][0]["name"] == "Imatinib"

    def test_search_with_filters(self):
        with patch(
            "compound_library.compound_searcher.CompoundSearcher",
            return_value=self._mock_searcher(),
        ):
            response = client.post(
                "/v1/compounds/search",
                json={
                    "query": "kinase inhibitor",
                    "filters": {"therapeutic_area": "Oncology"},
                    "limit": 10,
                },
            )
        assert response.status_code == 200

    def test_search_query_too_short(self):
        response = client.post("/v1/compounds/search", json={"query": "ki"})
        assert response.status_code == 422

    def test_search_limit_out_of_range(self):
        response = client.post(
            "/v1/compounds/search", json={"query": "kinase inhibitor", "limit": 0}
        )
        assert response.status_code == 422

    def test_search_qdrant_unavailable(self):
        with patch(
            "compound_library.compound_searcher.CompoundSearcher",
            side_effect=Exception("connection failed"),
        ):
            response = client.post(
                "/v1/compounds/search", json={"query": "kinase inhibitor"}
            )
        assert response.status_code == 503


# ---------------------------------------------------------------------------
# Clinical Trials
# ---------------------------------------------------------------------------


class TestClinicalTrials:
    def _create_trial(self, trial_id="T-001", arms=None):
        if arms is None:
            arms = ["placebo", "drug_10mg"]
        response = client.post(
            "/v1/trials",
            json={"trial_id": trial_id, "arms": arms},
        )
        return response

    def test_create_trial_success(self):
        from api.main import _trial_registry

        _trial_registry.clear()

        response = self._create_trial()
        assert response.status_code == 200
        data = response.json()
        assert data["trial_id"] == "T-001"
        assert data["status"] == "created"

    def test_create_trial_duplicate(self):
        from api.main import _trial_registry

        _trial_registry.clear()

        self._create_trial("T-DUP")
        # Second create with same ID
        response = client.post(
            "/v1/trials",
            json={"trial_id": "T-DUP", "arms": ["arm_a", "arm_b"]},
        )
        assert response.status_code == 409

    def test_create_trial_non_unique_arms(self):
        response = client.post(
            "/v1/trials",
            json={"trial_id": "T-BAD", "arms": ["arm_a", "arm_a"]},
        )
        assert response.status_code == 422

    def test_allocate_patient(self):
        from api.main import _trial_registry

        _trial_registry.clear()

        self._create_trial("T-ALLOC", arms=["placebo", "drug"])

        response = client.post("/v1/trials/T-ALLOC/allocate")
        assert response.status_code == 200
        data = response.json()
        assert data["allocated_arm"] in ["placebo", "drug"]
        assert "enrolled_counts" in data

    def test_allocate_patient_not_found(self):
        from api.main import _trial_registry

        _trial_registry.clear()

        response = client.post("/v1/trials/NONEXISTENT/allocate")
        assert response.status_code == 404

    def test_record_outcome_success(self):
        from api.main import _trial_registry

        _trial_registry.clear()

        self._create_trial("T-OUT", arms=["placebo", "drug"])

        response = client.post(
            "/v1/trials/T-OUT/outcome",
            json={"arm": "placebo", "success": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["arm"] == "placebo"
        assert data["success"] is True

    def test_record_outcome_invalid_arm(self):
        from api.main import _trial_registry

        _trial_registry.clear()

        self._create_trial("T-INV-ARM", arms=["placebo", "drug"])

        response = client.post(
            "/v1/trials/T-INV-ARM/outcome",
            json={"arm": "nonexistent", "success": True},
        )
        assert response.status_code == 400

    def test_check_eligibility_eligible(self):
        patient = {
            "patient_id": "P001",
            "age": 55,
            "sex": "F",
            "genomic_variants": [{"gene": "APOE", "variant": "e4"}],
            "comorbidities": [],
            "biomarkers": {},
            "medications": [],
            "prior_trials": [],
        }
        trial = {
            "trial_id": "T001",
            "min_age": 40,
            "max_age": 65,
            "required_markers": ["APOE"],
            "excluded_comorbidities": [],
        }
        response = client.post(
            "/v1/trials/eligibility", json={"patient": patient, "trial": trial}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is True

    def test_check_eligibility_ineligible_age(self):
        patient = {
            "patient_id": "P002",
            "age": 80,
            "sex": "M",
            "genomic_variants": [],
            "comorbidities": [],
            "biomarkers": {},
            "medications": [],
            "prior_trials": [],
        }
        trial = {
            "trial_id": "T002",
            "min_age": 18,
            "max_age": 75,
            "required_markers": [],
            "excluded_comorbidities": [],
        }
        response = client.post(
            "/v1/trials/eligibility", json={"patient": patient, "trial": trial}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is False


# ---------------------------------------------------------------------------
# GWAS Analysis
# ---------------------------------------------------------------------------


class TestGWASAnalysis:
    def _variant(self, variant_id, chrom="1", pos=100_000, maf=0.2):
        return {
            "variant_id": variant_id,
            "chromosome": chrom,
            "position": pos,
            "ref_allele": "A",
            "alt_allele": "G",
            "maf": maf,
            "hwe_p": 0.5,
            "missingness": 0.01,
        }

    def test_gwas_run_success(self):
        variants = [self._variant(f"rs{i}", pos=(i + 1) * 100_000) for i in range(5)]
        # Strong signal for first variant, null for rest
        cases = [[100, 900]] + [[500, 500]] * 4
        controls = [[850, 150]] + [[500, 500]] * 4

        response = client.post(
            "/v1/gwas/run",
            json={
                "variants": variants,
                "case_allele_counts": cases,
                "control_allele_counts": controls,
                "correction_method": "bonferroni",
                "association_method": "chi_square",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "n_variants_tested" in data
        assert "n_significant" in data
        assert "top_hits" in data

    def test_gwas_invalid_correction_method(self):
        response = client.post(
            "/v1/gwas/run",
            json={
                "variants": [self._variant("rs1")],
                "case_allele_counts": [[500, 500]],
                "control_allele_counts": [[500, 500]],
                "correction_method": "invalid",
                "association_method": "chi_square",
            },
        )
        assert response.status_code == 422

    def test_gwas_mismatched_lengths(self):
        response = client.post(
            "/v1/gwas/run",
            json={
                "variants": [self._variant("rs1"), self._variant("rs2")],
                "case_allele_counts": [[500, 500]],  # only 1, mismatch
                "control_allele_counts": [[500, 500], [500, 500]],
                "correction_method": "bonferroni",
                "association_method": "chi_square",
            },
        )
        assert response.status_code == 422

    def test_gwas_invalid_association_method(self):
        response = client.post(
            "/v1/gwas/run",
            json={
                "variants": [self._variant("rs1")],
                "case_allele_counts": [[500, 500]],
                "control_allele_counts": [[500, 500]],
                "correction_method": "bonferroni",
                "association_method": "bad_method",
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Drug Discovery
# ---------------------------------------------------------------------------


class TestDrugDiscoveryEndpoints:
    def test_run_without_credentials_returns_pending(self):
        env_patch = {}
        env_patch.pop("OPENAI_API_KEY", None)
        env_patch.pop("ANTHROPIC_API_KEY", None)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("ANTHROPIC_API_KEY", None)
            response = client.post(
                "/v1/drug-discovery/run",
                json={"disease": "Alzheimer's disease"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("pending_credentials", "unavailable")

    def test_run_disease_too_short(self):
        response = client.post("/v1/drug-discovery/run", json={"disease": "Al"})
        assert response.status_code == 422

    def test_list_agents_unavailable(self):
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", False):
            response = client.get("/v1/drug-discovery/agents")
        assert response.status_code == 503

    def test_list_agents_available(self):
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True):
            response = client.get("/v1/drug-discovery/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5
