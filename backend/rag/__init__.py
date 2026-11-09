"""
RAG Pipeline Package - Unified RAG pipeline for GNDEC chatbot.
"""

from .contracts import (
    GenerationInput,
    GenerationOutput,
    PersistenceRecord,
    PipelineContext,
    PolicyInput,
    PolicyOutput,
    PolicyDecision,
    ResolutionInput,
    ResolutionOutput,
    ResolutionStrategy,
    RetrievalInput,
    RetrievalOutput,
    RetrievalResult,
    RetrievalSource,
    VerificationInput,
    VerificationOutput,
    VerificationStatus,
)

from .memory import ResilientMemory, get_resilient_memory, reset_global_memory
from .pipeline import RAGPipeline, answer_query, create_default_pipeline

__all__ = [
    # Contracts
    "PipelineContext",
    "PolicyInput",
    "PolicyOutput",
    "PolicyDecision",
    "ResolutionInput",
    "ResolutionOutput",
    "ResolutionStrategy",
    "RetrievalInput",
    "RetrievalOutput",
    "RetrievalResult",
    "RetrievalSource",
    "GenerationInput",
    "GenerationOutput",
    "VerificationInput",
    "VerificationOutput",
    "VerificationStatus",
    "PersistenceRecord",
    # Memory
    "ResilientMemory",
    "get_resilient_memory",
    "reset_global_memory",
    # Pipeline
    "RAGPipeline",
    "answer_query",
    "create_default_pipeline",
]