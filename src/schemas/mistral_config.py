"""Mistral Integration Configuration Schemas"""

from typing import List, Optional
from pydantic import BaseModel


class MistralModelConfig(BaseModel):
    """Configuration for Mistral AI models."""

    chat_model: str = "mistral-large-latest"
    embedding_model: str = "mistral-embed"
    multimodal_model: str = "pixtral-12b-2409"
    temperature: float = 0.1
    max_tokens: Optional[int] = None


class RouterStrategy(BaseModel):
    """Schema for Kalibr-Mistral routing strategies."""

    primary_paths: List[str]
    fallback_paths: List[str]
    optimization_metric: str = "accuracy"
