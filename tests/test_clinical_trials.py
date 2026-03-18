"""Tests for clinical trials optimization engine."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from clinical_trials.realtime_optimizer import (
    AdaptiveTrialDesign,
    RealTimePatientMatcher,
    SafetyMonitoringSystem,
    PatientProfile,
)


class TestAdaptiveTrialDesign:
    """Test adaptive trial design with Thompson sampling."""

    @pytest.fixture
    def trial(self):
        """Create test trial instance."""
        with patch("clinical_trials.realtime_optimizer.KafkaProducer"):
            return AdaptiveTrialDesign(
                trial_id="TEST-001",
                arms=["placebo", "drug_10mg", "drug_20mg"],
                kafka_bootstrap="localhost:9092",
            )

    def test_initialization(self, trial):
        """Test trial initializes with correct priors."""
        assert trial.trial_id == "TEST-001"
        assert len(trial.arms) == 3
        assert all(trial.successes[arm] == 1.0 for arm in trial.arms)
        assert all(trial.failures[arm] == 1.0 for arm in trial.arms)
        assert all(trial.enrolled[arm] == 0 for arm in trial.arms)

    def test_allocate_next_patient(self, trial):
        """Test Thompson sampling allocation."""
        arm = trial.allocate_next_patient()
        assert arm in trial.arms
        assert trial.enrolled[arm] == 1

    def test_update_outcome_success(self, trial):
        """Test updating with successful outcome."""
        trial.allocate_next_patient()
        initial_success = trial.successes["placebo"]
        trial.update_outcome("placebo", True)
        assert trial.successes["placebo"] == initial_success + 1

    def test_update_outcome_failure(self, trial):
        """Test updating with failed outcome."""
        trial.allocate_next_patient()
        initial_failure = trial.failures["placebo"]
        trial.update_outcome("placebo", False)
        assert trial.failures["placebo"] == initial_failure + 1

    def test_context_manager(self, trial):
        """Test resource cleanup with context manager."""
        with trial as t:
            assert t == trial
        # Producer should be closed after context exit

    def test_empty_arms_list(self):
        """Test that empty arms list raises error."""
        with pytest.raises(Exception):
            with patch("clinical_trials.realtime_optimizer.KafkaProducer"):
                trial = AdaptiveTrialDesign(
                    trial_id="TEST-002", arms=[], kafka_bootstrap="localhost:9092"
                )
                trial.allocate_next_patient()


class TestRealTimePatientMatcher:
    """Test AI-powered patient matching."""

    @pytest.fixture
    def matcher(self):
        """Create test matcher instance."""
        with patch("clinical_trials.realtime_optimizer.qdrant_client.QdrantClient"):
            return RealTimePatientMatcher(qdrant_host="localhost", qdrant_port=6333)

    @pytest.fixture
    def patient(self):
        """Create test patient profile."""
        return PatientProfile(
            patient_id="P001",
            age=65,
            sex="M",
            genomic_variants=[{"gene": "APOE", "variant": "e4/e4"}],
            comorbidities=["hypertension"],
            biomarkers={"amyloid_beta": 1200.0},
            medications=["metoprolol"],
            prior_trials=[],
        )

    def test_check_eligibility_age_criteria(self, matcher, patient):
        """Test age-based eligibility."""
        trial = {
            "trial_id": "T001",
            "min_age": 18,
            "max_age": 75,
            "required_markers": [],
            "excluded_comorbidities": [],
        }
        assert matcher.check_eligibility(patient, trial) is True

        trial["max_age"] = 60
        assert matcher.check_eligibility(patient, trial) is False

    def test_check_eligibility_genomic_markers(self, matcher, patient):
        """Test genomic marker requirements."""
        trial = {
            "trial_id": "T001",
            "min_age": 18,
            "max_age": 75,
            "required_markers": ["APOE"],
            "excluded_comorbidities": [],
        }
        assert matcher.check_eligibility(patient, trial) is True

        trial["required_markers"] = ["BRCA1"]
        assert matcher.check_eligibility(patient, trial) is False

    def test_check_eligibility_comorbidity_exclusions(self, matcher, patient):
        """Test comorbidity exclusion criteria."""
        trial = {
            "trial_id": "T001",
            "min_age": 18,
            "max_age": 75,
            "required_markers": [],
            "excluded_comorbidities": ["diabetes"],
        }
        assert matcher.check_eligibility(patient, trial) is True

        trial["excluded_comorbidities"] = ["hypertension"]
        assert matcher.check_eligibility(patient, trial) is False


class TestSafetyMonitoringSystem:
    """Test real-time safety monitoring."""

    @pytest.fixture
    def monitor(self):
        """Create test safety monitor."""
        return SafetyMonitoringSystem(trial_id="TEST-001", safety_threshold=0.15)

    def test_initialization(self, monitor):
        """Test safety monitor initializes correctly."""
        assert monitor.trial_id == "TEST-001"
        assert monitor.safety_threshold == 0.15
        assert len(monitor.ae_buffer) == 0

    @pytest.mark.asyncio
    async def test_process_adverse_event(self, monitor):
        """Test adverse event processing."""
        from datetime import timezone
        event = {
            "trial_id": "TEST-001",
            "severity": 3,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await monitor.process_adverse_event(event)
        assert len(monitor.ae_buffer) == 1
