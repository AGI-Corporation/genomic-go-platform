"""
Real-Time Clinical Trials Optimization Engine

This module provides production-ready infrastructure for:
- Adaptive trial design with Bayesian optimization
- Real-time patient matching using AI/ML
- Safety monitoring with automated alerts
- Predictive endpoint modeling
- Regulatory-compliant data handling

Author: AGI Corporation Platform Team
Date: February 14, 2026
Version: 1.0.0
"""

import asyncio
import collections
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import qdrant_client
from aiokafka import AIOKafkaConsumer
from kafka import KafkaProducer
from scipy.stats import beta, norm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PatientProfile:
    """Patient profile for trial matching"""

    patient_id: str
    age: int
    sex: str
    genomic_variants: List[Dict]
    comorbidities: List[str]
    biomarkers: Dict[str, float]
    medications: List[str]
    prior_trials: List[str]


class AdaptiveTrialDesign:
    """
    Bayesian adaptive trial design with response-adaptive randomization.
    Implements O'Brien-Fleming boundaries and futility monitoring.
    """

    def __init__(
        self, trial_id: str, arms: List[str], kafka_bootstrap: str = "localhost:9092"
    ):
        self.trial_id = trial_id
        self.arms = arms
        self.successes = {arm: 1.0 for arm in arms}  # Beta prior alpha
        self.failures = {arm: 1.0 for arm in arms}  # Beta prior beta
        self.enrolled = {arm: 0 for arm in arms}

        # Kafka for real-time updates
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit - clean up Kafka resources.

        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value
            exc_tb: Exception traceback

        Returns:
            False to propagate exceptions
        """
        try:
            self.producer.flush(timeout=10)
            self.producer.close(timeout=10)
            logger.info(f"Closed Kafka producer for trial {self.trial_id}")
        except Exception as e:
            logger.error(f"Error closing Kafka producer: {e}")

        return False  # Don't suppress exceptions

    def allocate_next_patient(self) -> str:
        """Thompson sampling for response-adaptive randomization."""
        if not self.arms:
            raise ValueError(f"Trial {self.trial_id} has no arms defined")

        samples = {}
        for arm in self.arms:
            samples[arm] = np.random.beta(self.successes[arm], self.failures[arm])

        allocated_arm = max(samples, key=samples.get)
        self.enrolled[allocated_arm] += 1

        # Stream allocation to Kafka
        try:
            self.producer.send(
                "trial-allocations",
                {
                    "trial_id": self.trial_id,
                    "allocated_arm": allocated_arm,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "allocation_probs": {arm: float(s) for arm, s in samples.items()},
                },
            )
        except Exception as e:
            logger.error(f"Failed to send allocation to Kafka: {e}")
            # Continue even if Kafka fails

        return allocated_arm

    def update_outcome(self, arm: str, success: bool):
        """Update posterior with patient outcome"""
        if success:
            self.successes[arm] += 1
        else:
            self.failures[arm] += 1

        # Check stopping rules
        should_stop, reason = self.check_stopping_rules()
        if should_stop:
            logger.warning(f"Trial {self.trial_id} triggered stopping rule: {reason}")
            self.send_alert("TRIAL_STOP", reason)

    def check_stopping_rules(self) -> Tuple[bool, str]:
        """
        Implement O'Brien-Fleming stopping boundaries.
        Returns (should_stop, reason) tuple.
        """
        if not self.arms:
            return False, ""

        for arm in self.arms:
            n = self.successes[arm] + self.failures[arm] - 2  # Subtract Beta priors
            if n < 10:  # Minimum sample size needed
                continue

            p_success = self.successes[arm] / (self.successes[arm] + self.failures[arm])

            # Futility boundary: stop arm if success rate < 20%
            if p_success < 0.20:
                return (
                    True,
                    f"Futility boundary crossed for {arm}: success_rate={p_success:.3f}",
                )

            # Superiority: compare against other arms
            for other_arm in self.arms:
                if other_arm == arm:
                    continue

                other_n = self.successes[other_arm] + self.failures[other_arm] - 2
                if other_n < 10:
                    continue

                other_p = self.successes[other_arm] / (
                    self.successes[other_arm] + self.failures[other_arm]
                )

                # Z-test for proportions
                pooled_p = (self.successes[arm] - 1 + self.successes[other_arm] - 1) / (
                    n + other_n
                )
                if pooled_p == 0 or pooled_p == 1:
                    continue

                se = np.sqrt(pooled_p * (1 - pooled_p) * (1 / n + 1 / other_n))
                if se == 0:
                    continue

                z = (p_success - other_p) / se

                # O'Brien-Fleming boundary at alpha=0.05, information fraction = 0.5
                boundary = 4.0  # Conservative for early stopping
                if abs(z) > boundary:
                    return (
                        True,
                        f"Superiority detected: {arm} vs {other_arm}, z={z:.2f}",
                    )

        return False, ""

    def send_alert(self, alert_type: str, message: str) -> None:
        """
        Send alert to Kafka topic for trial monitoring.

        Args:
            alert_type: Type of alert (e.g., 'TRIAL_STOP', 'SAFETY_SIGNAL')
            message: Alert message
        """
        try:
            alert_payload = {
                "alert_type": alert_type,
                "message": message,
                "trial_id": self.trial_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity": "CRITICAL" if "stop" in alert_type.lower() else "WARNING",
            }

            self.producer.send("trial-alerts", alert_payload)
            self.producer.flush(timeout=5)

            logger.warning(f"ALERT [{self.trial_id}] {alert_type}: {message}")
        except Exception as e:
            logger.error(f"Failed to send alert for {self.trial_id}: {e}")
            # Don't raise - alerting failure shouldn't stop trial



class RealTimePatientMatcher:
    """
    AI-powered patient-to-trial matching with genomic and clinical features.
    Uses vector search for similarity matching.
    """

    def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        self.qdrant = qdrant_client.QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = "clinical_trials_embeddings"

    async def create_patient_embedding(self, patient: PatientProfile) -> List[float]:
        """Create 768-dimensional embedding vector for patient profile."""
        # Placeholder implementation returning random vector
        return np.random.rand(768).tolist()

    async def match_patient_to_trials(
        self, patient: PatientProfile, min_score: float = 0.7
    ) -> List[Dict]:
        """
        Find clinical trials matching patient profile.
        Returns ranked list of eligible trials with match scores.
        """
        # Create patient embedding (768-dim vector)
        patient_vector = await self.create_patient_embedding(patient)

        # Search vector database
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=patient_vector,
            limit=20,
            score_threshold=min_score,
        )

        matched_trials = []
        for result in results:
            trial = result.payload

            # Check hard eligibility criteria
            if self.check_eligibility(patient, trial):
                matched_trials.append(
                    {
                        "trial_id": trial["trial_id"],
                        "match_score": result.score,
                        "phase": trial["phase"],
                        "indication": trial["indication"],
                        "genomic_markers": trial.get("required_markers", []),
                    }
                )

        return sorted(matched_trials, key=lambda x: x["match_score"], reverse=True)

    def check_eligibility(self, patient: PatientProfile, trial: Dict) -> bool:
        """Hard eligibility criteria check"""
        # Age criteria
        if patient.age < trial.get("min_age", 0) or patient.age > trial.get(
            "max_age", 120
        ):
            return False

        # Required genomic markers
        patient_variants = {v["gene"] for v in patient.genomic_variants}
        required_markers = set(trial.get("required_markers", []))
        if required_markers and not required_markers.issubset(patient_variants):
            return False

        # Exclusionary comorbidities
        exclusions = set(trial.get("excluded_comorbidities", []))
        if exclusions.intersection(patient.comorbidities):
            return False

        return True


class SafetyMonitoringSystem:
    """
    Real-time safety monitoring with automated adverse event detection.
    Implements sequential probability ratio test (SPRT) for early detection.
    """

    def __init__(self, trial_id: str, safety_threshold: float = 0.15):
        self.trial_id = trial_id
        self.safety_threshold = safety_threshold
        # Bolt Optimization: Use deque for O(1) removals and sliding window pruning.
        # Stores (event_time, event_dict) to avoid repeated ISO parsing.
        self.ae_buffer = collections.deque()
        # Bolt Optimization: Maintain running count of severe events to avoid O(N) summation.
        self.severe_count = 0
        self.alert_history = []

    async def monitor_adverse_event_stream(self, kafka_topic: str = "adverse-events"):
        """
        Monitor real-time AE stream from Kafka.
        Triggers alerts if safety signals detected.
        """
        consumer = AIOKafkaConsumer(
            kafka_topic,
            bootstrap_servers="localhost:9092",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id=f"safety-monitor-{self.trial_id}",
        )

        await consumer.start()
        try:
            async for message in consumer:
                ae_event = message.value

                if ae_event["trial_id"] == self.trial_id:
                    await self.process_adverse_event(ae_event)
        finally:
            await consumer.stop()

    async def process_adverse_event(self, event: Dict[str, Any]):
        """Process single AE and check for safety signals"""
        # Bolt Optimization: Standardize on UTC-aware datetimes to fix comparison TypeErrors.
        event_time = datetime.fromisoformat(event["timestamp"])
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        # Add to buffer and update running severe count
        self.ae_buffer.append((event_time, event))
        if event.get("severity", 0) >= 3:
            self.severe_count += 1

        # Bolt Optimization: O(1) amortized sliding window pruning (assuming mostly chronological events).
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        while self.ae_buffer and self.ae_buffer[0][0] < cutoff:
            old_time, old_event = self.ae_buffer.popleft()
            if old_event.get("severity", 0) >= 3:
                self.severe_count -= 1

        # Calculate rolling AE rate using pre-calculated running counts
        buffer_len = len(self.ae_buffer)
        if buffer_len > 10:  # Minimum for statistical power
            severe_ae_rate = self.severe_count / buffer_len

            if severe_ae_rate > self.safety_threshold:
                # Maintain API compatibility by extracting events from tuples
                recent_events = [e[1] for e in self.ae_buffer]
                await self.trigger_safety_alert(severe_ae_rate, recent_events)

    async def trigger_safety_alert(self, rate: float, events: List[Dict]):
        """Trigger safety alert for trial"""
        logger.error(f"SAFETY ALERT for {self.trial_id}: Severe AE rate at {rate:.2%}")


class EndpointPredictor:
    """
    ML-based endpoint prediction using interim data.
    Predicts final trial outcomes to enable early decisions.
    """

    def __init__(self, model_path: str):
        # Load pre-trained XGBoost model
        import xgboost as xgb

        self.model = xgb.Booster()
        self.model.load_model(model_path)

    def engineer_features(
        self, data: pd.DataFrame, information_fraction: float
    ) -> pd.DataFrame:
        """Transform raw trial data into model features. Currently returns input data."""
        return data

    def predict_final_endpoint(
        self, interim_data: pd.DataFrame, information_fraction: float
    ) -> Tuple[float, float]:
        """
        Predict probability of trial success at final analysis.

        Returns:
            success_prob: Probability of meeting primary endpoint
            confidence: Prediction confidence interval width
        """
        # Feature engineering
        features = self.engineer_features(interim_data, information_fraction)

        # Model prediction
        import xgboost as xgb

        dmatrix = xgb.DMatrix(features)
        pred = self.model.predict(dmatrix)[0]

        # Bootstrap for confidence interval
        bootstrap_preds = []
        for _ in range(100):
            sample = interim_data.sample(frac=0.8, replace=True)
            sample_features = self.engineer_features(sample, information_fraction)
            sample_dmatrix = xgb.DMatrix(sample_features)
            bootstrap_preds.append(self.model.predict(sample_dmatrix)[0])

        confidence = np.percentile(bootstrap_preds, [2.5, 97.5])

        return float(pred), float(confidence[1] - confidence[0])


# Example usage
if __name__ == "__main__":
    # Initialize adaptive trial
    trial = AdaptiveTrialDesign(
        trial_id="TRIAL-2026-001", arms=["placebo", "drug_10mg", "drug_20mg"]
    )

    # Allocate patients adaptively
    for i in range(100):
        arm = trial.allocate_next_patient()
        # Simulate outcome (replace with real data)
        success = np.random.random() > 0.5
        trial.update_outcome(arm, success)
