"""
Unified RAG Pipeline - Policy → Resolution → Retrieval → Generation → Verification → Persistence

Orchestrates the complete answer generation flow with explicit contracts at each stage.
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Any, Callable, Optional

from .contracts import (
    GenerationInput,
    GenerationOutput,
    PersistenceRecord,
    PipelineContext,
    PolicyInput,
    PolicyOutput,
    ResolutionInput,
    ResolutionOutput,
    RetrievalInput,
    RetrievalOutput,
    RetrievalResult,
    RetrievalSource,
    ResolutionStrategy,
    VerificationInput,
    VerificationOutput,
    PolicyDecision,
    VerificationStatus,
)
from .memory import ResilientMemory

logger = logging.getLogger(__name__)


# Type aliases for pipeline stage functions
PolicyFn = Callable[[PolicyInput], Any]  # Returns PolicyOutput
ResolutionFn = Callable[[ResolutionInput], Any]  # Returns ResolutionOutput
RetrievalFn = Callable[[RetrievalInput], Any]  # Returns RetrievalOutput
GenerationFn = Callable[[GenerationInput], Any]  # Returns GenerationOutput
VerificationFn = Callable[[VerificationInput], Any]  # Returns VerificationOutput
PersistenceFn = Callable[[PersistenceRecord], Any]  # Returns bool


class RAGPipeline:
    """
    Unified RAG pipeline with explicit stage contracts.

    Each stage validates its input/output and can be independently tested.
    The pipeline accumulates context in PipelineContext for observability.
    """

    def __init__(
        self,
        policy_fn: PolicyFn,
        resolution_fn: ResolutionFn,
        retrieval_fn: RetrievalFn,
        generation_fn: GenerationFn,
        verification_fn: VerificationFn,
        persistence_fn: Optional[PersistenceFn] = None,
        memory: Optional[ResilientMemory] = None,
    ):
        self.policy_fn = policy_fn
        self.resolution_fn = resolution_fn
        self.retrieval_fn = retrieval_fn
        self.generation_fn = generation_fn
        self.verification_fn = verification_fn
        self.persistence_fn = persistence_fn
        self.memory = memory

    async def run(
        self,
        query: str,
        phone: str,
        session_id: str,
        language: str = "en",
        **kwargs,
    ) -> PipelineContext:
        """Execute the full pipeline and return complete context."""
        ctx = PipelineContext(
            phone=phone,
            session_id=session_id,
            query=query,
            language=language,
            metadata=kwargs,
        )

        try:
            # Stage 1: Policy
            ctx = await self._run_policy(ctx)
            if ctx.policy.decision != PolicyDecision.ALLOW:
                return await self._handle_policy_denial(ctx)

            # Stage 2: Resolution
            ctx = await self._run_resolution(ctx)

            # Stage 3: Retrieval
            ctx = await self._run_retrieval(ctx)

            # Stage 4: Generation
            ctx = await self._run_generation(ctx)

            # Stage 5: Verification
            ctx = await self._run_verification(ctx)

            # Stage 6: Persistence (only if verification passes)
            if self.persistence_fn and ctx.verification and ctx.verification.status == VerificationStatus.GROUNDED:
                await self._run_persistence(ctx)

            ctx.completed_at = time.time()
            return ctx

        except Exception as e:
            logger.error(f"[Pipeline] Error in pipeline: {e}", exc_info=True)
            ctx.errors.append(str(e))
            ctx.completed_at = time.time()
            return ctx

    async def _run_policy(self, ctx: PipelineContext) -> PipelineContext:
        """Execute policy evaluation stage."""
        logger.debug(f"[Pipeline] Running policy for query: {ctx.query[:50]}...")
        policy_input = PolicyInput(
            query=ctx.query,
            phone=ctx.phone,
            session_id=ctx.session_id,
            language=ctx.language,
            metadata=ctx.metadata,
        )
        ctx.policy = await self._call_async(self.policy_fn, policy_input)
        logger.debug(f"[Pipeline] Policy decision: {ctx.policy.decision}")
        return ctx

    async def _run_resolution(self, ctx: PipelineContext) -> PipelineContext:
        """Execute resolution planning stage."""
        logger.debug("[Pipeline] Running resolution")
        conv_history = await self._get_conversation_history(ctx)
        resolution_input = ResolutionInput(
            query=ctx.query,
            policy_output=ctx.policy,
            conversation_history=conv_history,
            session_context=ctx.metadata,
        )
        ctx.resolution = await self._call_async(self.resolution_fn, resolution_input)
        logger.debug(f"[Pipeline] Resolution strategy: {ctx.resolution.strategy}")
        return ctx

    async def _run_retrieval(self, ctx: PipelineContext) -> PipelineContext:
        """Execute retrieval stage."""
        logger.debug("[Pipeline] Running retrieval")
        retrieval_input = RetrievalInput(
            sub_queries=ctx.resolution.sub_queries or [ctx.query],
            strategy=ctx.resolution.strategy,
            top_k=5,
            filters=ctx.metadata.get("filters", {}),
        )
        ctx.retrieval = await self._call_async(self.retrieval_fn, retrieval_input)
        logger.debug(f"[Pipeline] Retrieved {ctx.retrieval.total_retrieved} documents")
        return ctx

    async def _run_generation(self, ctx: PipelineContext) -> PipelineContext:
        """Execute generation stage."""
        logger.debug("[Pipeline] Running generation")
        conv_history = await self._get_conversation_history(ctx)
        generation_input = GenerationInput(
            query=ctx.query,
            retrieval_output=ctx.retrieval,
            conversation_history=conv_history,
            system_prompt=ctx.metadata.get("system_prompt", ""),
            language=ctx.language,
            temperature=ctx.metadata.get("temperature", 0.1),
        )
        ctx.generation = await self._call_async(self.generation_fn, generation_input)
        logger.debug(f"[Pipeline] Generated answer ({len(ctx.generation.answer)} chars)")
        return ctx

    async def _run_verification(self, ctx: PipelineContext) -> PipelineContext:
        """Execute verification stage."""
        logger.debug("[Pipeline] Running verification")
        verification_input = VerificationInput(
            query=ctx.query,
            generation_output=ctx.generation,
            retrieval_output=ctx.retrieval,
            threshold=ctx.metadata.get("verification_threshold", 0.7),
        )
        ctx.verification = await self._call_async(self.verification_fn, verification_input)
        logger.debug(f"[Pipeline] Verification: {ctx.verification.status} ({ctx.verification.confidence:.2f})")
        return ctx

    async def _run_persistence(self, ctx: PipelineContext) -> PipelineContext:
        """Execute persistence stage."""
        logger.debug("[Pipeline] Running persistence")
        record = PersistenceRecord(
            query=ctx.query,
            answer=ctx.generation.answer,
            citations=ctx.generation.citations,
            phone=ctx.phone,
            session_id=ctx.session_id,
            strategy=ctx.resolution.strategy,
            verification_status=ctx.verification.status,
            verification_confidence=ctx.verification.confidence,
            metadata=ctx.metadata,
        )
        await self._call_async(self.persistence_fn, record)
        ctx.persistence = record
        return ctx

    async def _handle_policy_denial(self, ctx: PipelineContext) -> PipelineContext:
        """Handle policy denial/redirect/clarify cases."""
        if ctx.policy.decision == PolicyDecision.DENY:
            ctx.generation = GenerationOutput(
                answer=ctx.policy.reason or "I cannot answer that query.",
                metadata={"policy_decision": ctx.policy.decision.value},
            )
        elif ctx.policy.decision == PolicyDecision.REDIRECT:
            ctx.generation = GenerationOutput(
                answer=f"Please visit {ctx.policy.redirect_target} for this information.",
                metadata={"policy_decision": ctx.policy.decision.value, "redirect": ctx.policy.redirect_target},
            )
        elif ctx.policy.decision == PolicyDecision.CLARIFY:
            ctx.generation = GenerationOutput(
                answer=ctx.policy.clarification_prompt or "Could you please clarify your question?",
                metadata={"policy_decision": ctx.policy.decision.value},
            )
        ctx.completed_at = time.time()
        return ctx

    async def _get_conversation_history(self, ctx: PipelineContext) -> list[dict[str, str]]:
        """Get conversation history from memory."""
        if self.memory:
            try:
                mem = self.memory.get_memory(f"gndec:{ctx.phone}:{ctx.session_id}")
                hist_vars = mem.load_memory_variables({})
                hist_msgs = hist_vars.get("history", [])
                return [
                    {"type": m.type, "content": m.content}
                    for m in hist_msgs[-10:]  # Last 10 messages
                ]
            except Exception as e:
                logger.warning(f"[Pipeline] Failed to get conversation history: {e}")
        return []

    @staticmethod
    async def _call_async(fn: Callable, *args, **kwargs) -> Any:
        """Call function, handling both sync and async."""
        if asyncio.iscoroutinefunction(fn):
            return await fn(*args, **kwargs)
        return fn(*args, **kwargs)


def create_default_pipeline(
    *,
    memory: Optional[ResilientMemory] = None,
) -> RAGPipeline:
    """
    Create a pipeline with default stage implementations.

    The default stages use the existing backend modules.
    Override any stage by passing a custom function.
    """
    from . import policy, resolution, retrieval, generation, verification, persistence

    return RAGPipeline(
        policy_fn=policy.evaluate,
        resolution_fn=resolution.plan,
        retrieval_fn=retrieval.execute,
        generation_fn=generation.generate,
        verification_fn=verification.verify,
        persistence_fn=persistence.persist,
        memory=memory,
    )


async def answer_query(
    query: str,
    phone: str,
    session_id: str,
    language: str = "en",
    **kwargs,
) -> PipelineContext:
    """
    Convenience function to run the default pipeline.

    Returns the full PipelineContext for inspection.
    """
    pipeline = create_default_pipeline()
    return await pipeline.run(query, phone, session_id, language, **kwargs)