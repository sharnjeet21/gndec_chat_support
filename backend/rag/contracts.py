"""
Core data contracts for the unified RAG pipeline.

These define the immutable data structures that flow through:
Policy → Resolution → Retrieval → Generation → Verification → Persistence
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4


class PolicyDecision(str, Enum):
    """Outcome of policy evaluation for a query."""
    ALLOW = "allow"
    DENY = "deny"
    REDIRECT = "redirect"
    CLARIFY = "clarify"


class ResolutionStrategy(str, Enum):
    """Strategy selected for answering the query."""
    SINGLE_HOP = "single_hop"
    MULTI_HOP = "multi_hop"
    CACHED = "cached"
    DOMAIN_REDIRECT = "domain_redirect"
    ABSTAIN = "abstain"


class RetrievalSource(str, Enum):
    """Source of retrieved documents."""
    VECTOR_STORE = "vector_store"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    CACHE = "cache"
    GRAPH = "graph"


class VerificationStatus(str, Enum):
    """Result of groundedness verification."""
    GROUNDED = "grounded"
    PARTIALLY_GROUNDED = "partially_grounded"
    UNGROUNDED = "ungrounded"
    HALLUCINATED = "hallucinated"
    SENSITIVE = "sensitive"


@dataclass(frozen=True)
class PolicyInput:
    """Input to policy evaluation."""
    query: str
    phone: str
    session_id: str
    language: str = "en"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyOutput:
    """Result of policy evaluation."""
    decision: PolicyDecision
    reason: str
    redirect_target: Optional[str] = None
    clarification_prompt: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolutionInput:
    """Input to resolution planning."""
    query: str
    policy_output: PolicyOutput
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    session_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolutionOutput:
    """Result of resolution planning."""
    strategy: ResolutionStrategy
    sub_queries: list[str] = field(default_factory=list)
    reasoning: str = ""
    cache_key: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalInput:
    """Input to retrieval step."""
    sub_queries: list[str]
    strategy: ResolutionStrategy
    top_k: int = 5
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    """Result of a single retrieval operation."""
    query: str
    documents: list[dict[str, Any]]
    source: RetrievalSource
    scores: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    retrieved_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class RetrievalOutput:
    """Aggregated retrieval results for all sub-queries."""
    results: list[RetrievalResult]
    combined_documents: list[dict[str, Any]] = field(default_factory=list)
    total_retrieved: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationInput:
    """Input to generation step."""
    query: str
    retrieval_output: RetrievalOutput
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    system_prompt: str = ""
    language: str = "en"
    temperature: float = 0.1


@dataclass(frozen=True)
class GenerationOutput:
    """Result of generation step."""
    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    model: str = ""
    tokens_used: int = 0
    latency_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationInput:
    """Input to verification step."""
    query: str
    generation_output: GenerationOutput
    retrieval_output: RetrievalOutput
    threshold: float = 0.7


@dataclass(frozen=True)
class VerificationOutput:
    """Result of verification step."""
    status: VerificationStatus
    confidence: float
    issues: list[str] = field(default_factory=list)
    grounded_spans: list[dict[str, Any]] = field(default_factory=list)
    ungrounded_spans: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PersistenceRecord:
    """Record persisted after successful verification."""
    id: str = field(default_factory=lambda: str(uuid4()))
    query: str = ""
    answer: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    phone: str = ""
    session_id: str = ""
    strategy: ResolutionStrategy = ResolutionStrategy.SINGLE_HOP
    verification_status: VerificationStatus = VerificationStatus.GROUNDED
    verification_confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineContext:
    """Complete context flowing through the pipeline."""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    phone: str = ""
    session_id: str = ""
    query: str = ""
    language: str = "en"
    policy: Optional[PolicyOutput] = None
    resolution: Optional[ResolutionOutput] = None
    retrieval: Optional[RetrievalOutput] = None
    generation: Optional[GenerationOutput] = None
    verification: Optional[VerificationOutput] = None
    persistence: Optional[PersistenceRecord] = None
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)