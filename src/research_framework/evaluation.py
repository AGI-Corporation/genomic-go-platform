"""RAG & Research Evaluation Framework

Uses Mistral's structured output capabilities to act as an LLM-as-a-Judge,
evaluating the quality, relevance, and groundedness of research findings.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Any
from src.integrations.mistral_adapter import MistralGenomicAdapter


class Score(str, Enum):
    no_relevance = "0"
    low_relevance = "1"
    medium_relevance = "2"
    high_relevance = "3"


SCORE_DESCRIPTION = (
    "Score as a string between '0' and '3'. "
    "0: No relevance/Not grounded - Irrelevant. "
    "1: Low relevance/Somewhat relevant. "
    "2: Medium relevance/Mostly relevant. "
    "3: High relevance/Fully relevant."
)


class EvaluationCriterion(BaseModel):
    explanation: str = Field(..., description="Step-by-step reasoning for the score.")
    score: Score = Field(..., description=SCORE_DESCRIPTION)


class ResearchEvaluation(BaseModel):
    scientific_accuracy: EvaluationCriterion = Field(
        ..., description="Evaluation of factual correctness."
    )
    clinical_relevance: EvaluationCriterion = Field(
        ..., description="Evaluation of potential clinical impact."
    )
    groundedness: EvaluationCriterion = Field(
        ..., description="How faithful the findings are to the source data."
    )


class ResearchJudge:
    """Uses Mistral to evaluate genomic research outputs."""

    def __init__(self, api_key: Optional[str] = None):
        self.adapter = MistralGenomicAdapter(api_key)

    async def evaluate_discovery(
        self, query: str, context: str, findings: str
    ) -> ResearchEvaluation:
        """Evaluates a research discovery against criteria using Mistral Judge."""
        prompt = f"""
        You are a scientific judge evaluating a genomic research finding.
        Query: {query}
        Retrieved Data/Context: {context}
        Generated Findings: {findings}

        Evaluate the findings based on Scientific Accuracy, Clinical Relevance, and Groundedness.
        """

        return await self.adapter.parse_structured_output(prompt, ResearchEvaluation)


if __name__ == "__main__":
    print("Research Evaluation Module Loaded.")
