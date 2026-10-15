"""Local language model adapters, medical prompts, and RAG pipeline."""

from app.llm.ollama_client import (
    LLMGenerationResult,
    LocalServiceUnavailable,
    ModelUnavailableError,
    OllamaClient,
)
from app.llm.prompts import HEALTHCARE_SYSTEM_PROMPT, build_grounded_prompt
from app.llm.rag_pipeline import HealthcareRAGPipeline, RAGResponse

__all__ = [
    "HEALTHCARE_SYSTEM_PROMPT",
    "HealthcareRAGPipeline",
    "LLMGenerationResult",
    "LocalServiceUnavailable",
    "ModelUnavailableError",
    "OllamaClient",
    "RAGResponse",
    "build_grounded_prompt",
]
