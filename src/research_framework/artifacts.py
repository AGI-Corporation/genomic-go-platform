"""Agent Artifact Registry

Provides a centralized management system for sharing biological artifacts
(e.g., PDB structures, genomic datasets, leads) produced by the research swarm.
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from src.schemas.genomic_entities import AgentArtifact


class ArtifactRegistry:
    """Manages storage and retrieval of research artifacts produced by agents."""

    def __init__(self, storage_path: str = "lab_notebook/artifacts"):
        self.storage_path = storage_path
        self.artifacts: Dict[str, AgentArtifact] = {}
        os.makedirs(self.storage_path, exist_ok=True)

    def register_artifact(
        self,
        agent_id: str,
        artifact_type: str,
        data: Any,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """Registers a new artifact in the registry and persists it to disk."""
        artifact_id = f"ART_{int(datetime.now(timezone.utc).timestamp())}"
        artifact = AgentArtifact(
            artifact_id=artifact_id,
            agent_id=agent_id,
            type=artifact_type,
            data=data,
            metadata=metadata or {},
        )

        self.artifacts[artifact_id] = artifact
        self._persist_artifact(artifact)
        return artifact_id

    def get_artifact(self, artifact_id: str) -> Optional[AgentArtifact]:
        """Retrieves an artifact by its ID."""
        return self.artifacts.get(artifact_id)

    def list_artifacts(self, artifact_type: str = None) -> List[AgentArtifact]:
        """Lists artifacts, optionally filtered by type."""
        if artifact_type:
            return [a for a in self.artifacts.values() if a.type == artifact_type]
        return list(self.artifacts.values())

    def _persist_artifact(self, artifact: AgentArtifact):
        """Persists the artifact to a JSON file on disk."""
        file_path = os.path.join(self.storage_path, f"{artifact.artifact_id}.json")
        with open(file_path, "w") as f:
            f.write(artifact.model_dump_json(indent=2))


if __name__ == "__main__":
    registry = ArtifactRegistry()
    print("Artifact Registry Initialized.")
