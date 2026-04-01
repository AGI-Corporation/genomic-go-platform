"""Robotics & Lab Automation Integration with Real-Time Clinical Trial Data

This module integrates robotics systems, automated lab equipment, and wearables
for real-time clinical trial data collection and genomic research automation.

Supported Systems:
- NANDA robotics protocol
- Automated liquid handlers (Hamilton, Tecan, Agilent)
- High-throughput screening systems
- Wearable biometric monitoring
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncio

logger = logging.getLogger(__name__)

# Kafka bootstrap servers from environment (falls back to localhost for dev)
_KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


class RoboticsAutomationManager:
    """Agent-driven control for automated lab equipment via NANDA protocol."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.nanda_endpoint: str = config.get("endpoint", "http://lab-robot-1.local")
        self.kafka_bootstrap: str = config.get(
            "kafka_bootstrap", _KAFKA_BOOTSTRAP
        )
        self.logger = logging.getLogger(f"{__name__}.RoboticsAutomationManager")
        self.active_protocols: List[str] = []
        self._kafka_producer = None

    def _get_kafka_producer(self):
        """Lazily initialise a Kafka producer, returning None if unavailable."""
        if self._kafka_producer is not None:
            return self._kafka_producer
        try:
            from kafka import KafkaProducer  # type: ignore

            self._kafka_producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except Exception as exc:
            self.logger.warning(f"Kafka producer unavailable: {exc}")
        return self._kafka_producer

    async def execute_protocol(
        self, protocol_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executes a predefined lab protocol with provided parameters."""
        if not protocol_name:
            raise ValueError("Protocol name must be specified")

        self.logger.info(
            f"Executing protocol: {protocol_name} with params: {parameters}"
        )

        result = await self._forward_to_nanda(protocol_name, parameters)

        # Publish protocol execution event to Kafka for audit and real-time monitoring
        self._publish_protocol_event(protocol_name, parameters, result)

        return result

    async def _forward_to_nanda(
        self, protocol_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Forward protocol execution request to the NANDA hardware control endpoint.

        The NANDA endpoint accepts a JSON payload with protocol name and parameters
        and returns an execution status. Falls back to a simulated response when the
        endpoint is unavailable (e.g., in development/CI environments).
        """
        import aiohttp  # type: ignore

        payload = {
            "protocol": protocol_name,
            "params": parameters,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.nanda_endpoint}/execute",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response.raise_for_status()
                    nanda_result = await response.json()
                    self.logger.info(
                        f"NANDA endpoint returned status={nanda_result.get('status')} "
                        f"for protocol '{protocol_name}'"
                    )
                    return {
                        "status": nanda_result.get("status", "success"),
                        "protocol": protocol_name,
                        "applied_parameters": parameters,
                        "nanda_response": nanda_result,
                        "timestamp": datetime.now().isoformat(),
                    }
        except Exception as exc:
            # Log the error but return a structured result so callers can handle gracefully
            self.logger.warning(
                f"NANDA endpoint '{self.nanda_endpoint}' unreachable for protocol "
                f"'{protocol_name}': {exc}. Using simulated response."
            )
            return {
                "status": "simulated",
                "protocol": protocol_name,
                "applied_parameters": parameters,
                "timestamp": datetime.now().isoformat(),
            }

    def _publish_protocol_event(
        self,
        protocol_name: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Publish a protocol execution event to the Kafka 'lab-protocols' topic."""
        producer = self._get_kafka_producer()
        if producer is None:
            return

        event = {
            "event_type": "protocol_executed",
            "protocol": protocol_name,
            "parameters": parameters,
            "result_status": result.get("status"),
            "timestamp": result.get("timestamp"),
        }
        try:
            producer.send("lab-protocols", event)
            producer.flush(timeout=5)
        except Exception as exc:
            self.logger.error(f"Failed to publish protocol event to Kafka: {exc}")


class WearableDataStreamer:
    """Ingests real-time data from clinical trial participant wearables."""

    KAFKA_TOPIC = "wearable-metrics"

    def __init__(
        self,
        trial_id: str,
        max_buffer_size: int = 1000,
        kafka_bootstrap: Optional[str] = None,
    ):
        self.trial_id = trial_id
        self.data_buffer: List[Dict[str, Any]] = []
        self.max_buffer_size = max_buffer_size
        self.kafka_bootstrap = kafka_bootstrap or _KAFKA_BOOTSTRAP
        self._kafka_producer = None

    def _get_kafka_producer(self):
        """Lazily initialise a Kafka producer, returning None if unavailable."""
        if self._kafka_producer is not None:
            return self._kafka_producer
        try:
            from kafka import KafkaProducer  # type: ignore

            self._kafka_producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except Exception as exc:
            logger.warning(f"Wearable Kafka producer unavailable: {exc}")
        return self._kafka_producer

    async def ingest_real_time_data(
        self, device_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ingest a real-time biometric event from a wearable device.

        The event is:
        1. Buffered locally for in-process analysis.
        2. Streamed to the Kafka 'wearable-metrics' topic for downstream
           real-time processing by the SafetyMonitoringSystem and other consumers.
        """
        timestamp = datetime.now().isoformat()
        entry: Dict[str, Any] = {
            "device_id": device_id,
            "data": data,
            "timestamp": timestamp,
            "trial_id": self.trial_id,
        }

        # Stream to Kafka for real-time analysis
        self._stream_to_kafka(entry)

        # Local circular buffer for in-process queries
        self.data_buffer.append(entry)
        if len(self.data_buffer) > self.max_buffer_size:
            self.data_buffer.pop(0)

        return entry

    def _stream_to_kafka(self, entry: Dict[str, Any]) -> None:
        """Publish a wearable event to the Kafka 'wearable-metrics' topic."""
        producer = self._get_kafka_producer()
        if producer is None:
            return

        try:
            producer.send(self.KAFKA_TOPIC, entry)
            # Non-blocking flush – we don't block the ingestion path
            producer.flush(timeout=2)
        except Exception as exc:
            logger.error(
                f"Failed to stream wearable event to Kafka topic "
                f"'{self.KAFKA_TOPIC}': {exc}"
            )


# Example integration demo
if __name__ == "__main__":

    async def demo():
        manager = RoboticsAutomationManager({"endpoint": "http://lab-robot-1.local"})
        streamer = WearableDataStreamer("TRIAL-2026-X")

        # Simulate trial data triggering robotics
        wearable_event = await streamer.ingest_real_time_data(
            "WATCH-123", {"heart_rate": 110, "stress_level": "high"}
        )

        if wearable_event["data"]["stress_level"] == "high":
            result = await manager.execute_protocol(
                "ADJUST_SAMPLE_TREATMENT",
                {"sample_id": "SAM-99", "adjustment": "increase_dilution"},
            )
            print(f"Robotics action taken: {result['status']}")

    # asyncio.run(demo())
