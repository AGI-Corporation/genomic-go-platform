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
        event = {
            "trial_id": "TEST-001",
            "severity": 3,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await monitor.process_adverse_event(event)
        assert len(monitor.ae_buffer) == 1

    @pytest.mark.asyncio
    async def test_process_adverse_event_multiple(self, monitor):
        """Test that multiple events are all buffered."""
        for i in range(5):
            event = {
                "trial_id": "TEST-001",
                "severity": 1,
                "timestamp": datetime.utcnow().isoformat(),
            }
            await monitor.process_adverse_event(event)
        assert len(monitor.ae_buffer) == 5

    @pytest.mark.asyncio
    async def test_process_adverse_event_triggers_safety_alert(self, monitor):
        """Test that high severe AE rate triggers a safety alert."""
        # Add 11 events with high severity to exceed threshold
        for _ in range(11):
            event = {
                "trial_id": "TEST-001",
                "severity": 4,
                "timestamp": datetime.utcnow().isoformat(),
            }
            monitor.ae_buffer.append(event)

        event = {
            "trial_id": "TEST-001",
            "severity": 4,
            "timestamp": datetime.utcnow().isoformat(),
        }
        with patch.object(monitor, "trigger_safety_alert") as mock_alert:
            await monitor.process_adverse_event(event)
            mock_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_adverse_event_no_alert_below_threshold(self, monitor):
        """Test that low severe AE rate does not trigger alert even with enough samples."""
        # Add 11 mild events (severity 1, below threshold of 3)
        for _ in range(11):
            event = {
                "trial_id": "TEST-001",
                "severity": 1,
                "timestamp": datetime.utcnow().isoformat(),
            }
            monitor.ae_buffer.append(event)

        mild_event = {
            "trial_id": "TEST-001",
            "severity": 1,
            "timestamp": datetime.utcnow().isoformat(),
        }
        with patch.object(monitor, "trigger_safety_alert") as mock_alert:
            await monitor.process_adverse_event(mild_event)
            mock_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_safety_alert_logs_error(self, monitor):
        """Test that trigger_safety_alert logs an error."""
        events = [
            {
                "trial_id": "TEST-001",
                "severity": 4,
                "timestamp": datetime.utcnow().isoformat(),
            }
        ]
        # Should not raise; logs error internally
        await monitor.trigger_safety_alert(0.25, events)


class TestAdaptiveTrialDesignStoppingRules:
    """Test O'Brien-Fleming stopping rules."""

    @pytest.fixture
    def trial(self):
        """Create test trial with mocked Kafka."""
        with patch("clinical_trials.realtime_optimizer.KafkaProducer"):
            return AdaptiveTrialDesign(
                trial_id="TEST-STOP",
                arms=["control", "treatment"],
                kafka_bootstrap="localhost:9092",
            )

    def test_check_stopping_rules_insufficient_samples(self, trial):
        """Test no stopping signal when sample size is below minimum."""
        should_stop, reason = trial.check_stopping_rules()
        assert should_stop is False
        assert reason == ""

    def test_check_stopping_rules_futility_boundary(self, trial):
        """Test futility boundary triggers stop when success rate < 20%."""
        # Set control arm to have low success rate with enough samples
        # n = successes + failures - 2 >= 10 -> need at least 12 total
        trial.successes["control"] = 1.0  # 1 success (including prior)
        trial.failures["control"] = 12.0  # 12 failures -> p = 1/13 ≈ 0.077

        should_stop, reason = trial.check_stopping_rules()
        assert should_stop is True
        assert "Futility" in reason
        assert "control" in reason

    def test_check_stopping_rules_superiority_boundary(self, trial):
        """Test superiority boundary triggers stop with large z-score."""
        # Treatment arm: high success (p=0.80, n=98)
        trial.successes["treatment"] = 80.0
        trial.failures["treatment"] = 20.0
        # Control arm: low but above futility threshold (p≈0.216, n=100)
        trial.successes["control"] = 22.0
        trial.failures["control"] = 80.0

        should_stop, reason = trial.check_stopping_rules()
        assert should_stop is True
        assert "Superiority" in reason

    def test_check_stopping_rules_no_stop_when_similar(self, trial):
        """Test no stopping when arm performance is similar."""
        # Both arms at 50% success with 12 total outcomes
        trial.successes["control"] = 7.0
        trial.failures["control"] = 7.0
        trial.successes["treatment"] = 7.0
        trial.failures["treatment"] = 7.0

        should_stop, reason = trial.check_stopping_rules()
        assert should_stop is False

    def test_send_alert_success(self, trial):
        """Test send_alert sends message to Kafka producer."""
        trial.send_alert("TRIAL_STOP", "Futility boundary crossed")
        trial.producer.send.assert_called_once()
        trial.producer.flush.assert_called()

    def test_send_alert_kafka_failure_does_not_raise(self, trial):
        """Test send_alert does not propagate Kafka errors."""
        trial.producer.send.side_effect = Exception("Kafka unavailable")
        # Should not raise
        trial.send_alert("SAFETY_SIGNAL", "High AE rate detected")


class TestRealTimePatientMatcherAsync:
    """Test async methods of RealTimePatientMatcher."""

    @pytest.fixture
    def matcher(self):
        """Create test matcher with mocked Qdrant."""
        with patch("clinical_trials.realtime_optimizer.qdrant_client.QdrantClient"):
            return RealTimePatientMatcher(qdrant_host="localhost", qdrant_port=6333)

    @pytest.fixture
    def patient(self):
        """Create test patient profile."""
        return PatientProfile(
            patient_id="P002",
            age=50,
            sex="F",
            genomic_variants=[{"gene": "BRCA1", "variant": "pathogenic"}],
            comorbidities=[],
            biomarkers={"CA-125": 45.0},
            medications=[],
            prior_trials=[],
        )

    @pytest.mark.asyncio
    async def test_create_patient_embedding_returns_768_dims(self, matcher, patient):
        """Test that embedding vector has 768 dimensions."""
        embedding = await matcher.create_patient_embedding(patient)
        assert len(embedding) == 768
        assert all(isinstance(v, float) for v in embedding)

    @pytest.mark.asyncio
    async def test_match_patient_to_trials_returns_eligible(self, matcher, patient):
        """Test match_patient_to_trials returns eligible trials sorted by score."""
        mock_result = Mock()
        mock_result.payload = {
            "trial_id": "T-BRCA",
            "phase": "II",
            "indication": "Breast Cancer",
            "min_age": 18,
            "max_age": 75,
            "required_markers": ["BRCA1"],
            "excluded_comorbidities": [],
        }
        mock_result.score = 0.88

        matcher.qdrant.search.return_value = [mock_result]

        trials = await matcher.match_patient_to_trials(patient, min_score=0.7)
        assert len(trials) == 1
        assert trials[0]["trial_id"] == "T-BRCA"
        assert trials[0]["match_score"] == 0.88

    @pytest.mark.asyncio
    async def test_match_patient_to_trials_filters_ineligible(self, matcher, patient):
        """Test match_patient_to_trials excludes ineligible trials."""
        mock_result = Mock()
        mock_result.payload = {
            "trial_id": "T-OLD",
            "phase": "III",
            "indication": "Breast Cancer",
            "min_age": 60,  # patient is 50 -> ineligible
            "max_age": 75,
            "required_markers": [],
            "excluded_comorbidities": [],
        }
        mock_result.score = 0.91

        matcher.qdrant.search.return_value = [mock_result]

        trials = await matcher.match_patient_to_trials(patient, min_score=0.7)
        assert trials == []

    @pytest.mark.asyncio
    async def test_match_patient_to_trials_sorted_by_score(self, matcher, patient):
        """Test matched trials are returned sorted by descending match score."""
        def make_mock_result(trial_id, score):
            r = Mock()
            r.payload = {
                "trial_id": trial_id,
                "phase": "II",
                "indication": "Cancer",
                "min_age": 18,
                "max_age": 75,
                "required_markers": [],
                "excluded_comorbidities": [],
            }
            r.score = score
            return r

        matcher.qdrant.search.return_value = [
            make_mock_result("T-LOW", 0.72),
            make_mock_result("T-HIGH", 0.95),
            make_mock_result("T-MED", 0.83),
        ]

        trials = await matcher.match_patient_to_trials(patient)
        scores = [t["match_score"] for t in trials]
        assert scores == sorted(scores, reverse=True)
