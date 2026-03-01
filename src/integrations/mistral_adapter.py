"""Mistral AI Adapter for Genomic.go Platform

This module provides an integration with Mistral AI models to optimize
genomic analysis and agent reasoning during the Mistral Worldwide Hackathon.
"""

import os
from typing import List, Dict, Any, Optional
from mistralai import Mistral
from langchain_mistralai import ChatMistralAI


class MistralGenomicAdapter:
    """Adapter for Mistral AI models specialized for genomic research."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY must be set for MistralGenomicAdapter")

        self.client = Mistral(api_key=self.api_key)

    def get_langchain_model(
        self, model_name: str = "mistral-large-latest"
    ) -> ChatMistralAI:
        """Returns a LangChain compatible Mistral AI model."""
        return ChatMistralAI(
            model=model_name, mistral_api_key=self.api_key, temperature=0.1
        )

    async def analyze_genomic_data(self, data: str, prompt: str) -> str:
        """Analyze genomic data using Mistral AI models."""
        response = await self.client.chat.complete_async(
            model="mistral-large-latest",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert genomics research assistant.",
                },
                {"role": "user", "content": f"{prompt}\n\nData: {data}"},
            ],
        )
        return response.choices[0].message.content

    async def get_text_embedding(self, text: str) -> List[float]:
        """Generate embeddings for clinical/genomic text using Mistral."""
        response = await self.client.embeddings.create_async(
            model="mistral-embed", inputs=[text]
        )
        return response.data[0].embedding


class MistralOptimizedRouter:
    """Mistral-optimized routing for the Kalibr framework."""

    def __init__(self, api_key: Optional[str] = None):
        self.adapter = MistralGenomicAdapter(api_key)

    def get_router_config(self) -> Dict[str, Any]:
        """Returns configuration for Kalibr router to prioritize Mistral models."""
        return {
            "primary_model": "mistral-large-latest",
            "fallback_models": ["open-mistral-7b", "mistral-small-latest"],
            "optimization_goal": "cost_efficiency_for_genomics",
        }


if __name__ == "__main__":
    print("Mistral Adapter initialized for Mistral Worldwide Hackathon!")
