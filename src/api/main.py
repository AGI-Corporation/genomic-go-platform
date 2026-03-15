"""API Gateway for Genomic Swarm Framework

Provides a RESTful interface for external applications to trigger
genomic discovery pipelines and interact with the agent swarm.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List
from src.research_framework.discovery_tool import GenomicDiscoveryTool
from src.schemas.genomic_entities import ResearchDiscovery

app = FastAPI(title="Genomic.go API", version="1.0.0")
discovery_tool = GenomicDiscoveryTool()


class IndicationRequest(BaseModel):
    indication: str


@app.get("/")
def read_root():
    return {"status": "Genomic Swarm API Online", "version": "1.0.0"}


@app.post("/discover/indication", response_model=Dict[str, Any])
async def trigger_discovery(request: IndicationRequest):
    """Triggers an end-to-end genomic discovery pipeline for a specific disease."""
    try:
        report = await discovery_tool.accelerate_research(request.indication)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/status")
async def get_agent_swarm_status():
    """Returns the current status of the registered research agents."""
    return {
        "swarm_size": len(discovery_tool.swarm.orchestrator.agents),
        "agents": list(discovery_tool.swarm.orchestrator.agents.keys()),
        "orchestrator": "Mistral-Large-Latest",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
