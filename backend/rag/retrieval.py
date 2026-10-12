"""
Retrieval execution stage - retrieves documents for sub-queries using vector store,
keyword search, and SerpAPI live web search fallback.

Web search is triggered automatically when:
  1. FAISS/BM25 returns fewer documents than SERP_FALLBACK_THRESHOLD (default: 2)
  2. The query contains live-data keywords like 'latest', 'recent', '2025', 'notice', etc.

All thresholds and keys are read from .env — nothing is hardcoded.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any

from .contracts import RetrievalInput, RetrievalOutput, RetrievalResult, RetrievalSource

logger = logging.getLogger(__name__)


async def execute(input_: RetrievalInput) -> RetrievalOutput:
    """
    Execute retrieval for all sub-queries.

    Pipeline:
      1. FAISS + BM25 hybrid search (always)
      2. SerpAPI live web search (conditional — low FAISS count or live-data keywords)
      3. Deduplicate and merge results
    """
    from ..vectorstore import retrieve as vector_retrieve
    from ..web_search import search_gndec, should_trigger_web_search

    all_results: list[RetrievalResult] = []
    combined_docs: list[dict[str, Any]] = []
    seen_contents: set[str] = set()

    # Use the first sub-query as the primary query for web-search trigger decision
    primary_query = input_.sub_queries[0] if input_.sub_queries else ""

    # Start SerpAPI search concurrently if always-on or triggered by live keywords
    web_search_task: Optional[asyncio.Task] = None
    if should_trigger_web_search(primary_query, 0):
        logger.info(f"[Retrieval] Launching concurrent SerpAPI search for: {primary_query!r}")
        web_search_task = asyncio.create_task(search_gndec(primary_query))

    for sub_query in input_.sub_queries:
        try:
            # ── Stage 1: FAISS + BM25 Hybrid Retrieval ──────────────────────
            docs = await asyncio.to_thread(vector_retrieve, sub_query, k=input_.top_k)

            documents = []
            for doc in docs:
                doc_dict = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "source_file": doc.metadata.get("source_file", "unknown"),
                }
                documents.append(doc_dict)

                content_hash = doc.page_content[:200]
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    combined_docs.append(doc_dict)

            result = RetrievalResult(
                query=sub_query,
                documents=documents,
                source=RetrievalSource.HYBRID,
                scores=[doc.metadata.get("score", 0.0) for doc in docs],
                metadata={"retrieval_method": "vector_hybrid"},
            )
            all_results.append(result)

        except Exception as e:
            logger.error(f"[Retrieval] Failed for query '{sub_query}': {e}")
            all_results.append(RetrievalResult(
                query=sub_query,
                documents=[],
                source=RetrievalSource.HYBRID,
                metadata={"error": str(e)},
            ))

    # ── Stage 2: Gather or Trigger SerpAPI Live Web Search ──────────────────
    web_docs: list[dict] = []
    if web_search_task:
        try:
            web_docs = await web_search_task
        except Exception as e:
            logger.error(f"[Retrieval] Concurrent SerpAPI search failed: {e}")
    elif should_trigger_web_search(primary_query, len(combined_docs)):
        # Fallback if FAISS doc count was below threshold
        try:
            logger.info(f"[Retrieval] Triggering SerpAPI fallback for: {primary_query!r}")
            web_docs = await search_gndec(primary_query)
        except Exception as e:
            logger.error(f"[Retrieval] SerpAPI fallback failed: {e}")

    faiss_doc_count = len(combined_docs)
    if web_docs:
        web_added = 0
        for doc in web_docs:
            content_hash = doc["content"][:200]
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                combined_docs.append(doc)
                web_added += 1

        logger.info(f"[Retrieval] Added {web_added} live SerpAPI web search results to context")
        all_results.append(RetrievalResult(
            query=primary_query,
            documents=web_docs,
            source=RetrievalSource.HYBRID,
            metadata={"retrieval_method": "serpapi_web_search", "web_results": len(web_docs)},
        ))

        # Dynamically store newly retrieved web data into local vector DB for future queries
        try:
            from ..vectorstore import add_to_vector_db
            items_to_store = []
            for wd in web_docs:
                title = wd.get("title", "").strip()
                content = wd.get("content", "").strip()
                question = f"{primary_query} - {title}".strip(" -") if title else primary_query
                items_to_store.append({
                    "question": question,
                    "answer": content,
                    "section": "Web Search (GNDEC)",
                    "source_file": wd.get("url") or "gndec.ac.in",
                    "url": wd.get("url", ""),
                    "metadata": wd.get("metadata", {}),
                })
            asyncio.create_task(asyncio.to_thread(add_to_vector_db, items_to_store))
        except Exception as e:
            logger.warning(f"[Retrieval] Could not queue web results for vector DB indexing: {e}")

    return RetrievalOutput(
        results=all_results,
        combined_documents=combined_docs,
        total_retrieved=len(combined_docs),
        metadata={
            "sub_query_count": len(input_.sub_queries),
            "faiss_docs": faiss_doc_count,
            "web_search_triggered": len(combined_docs) > faiss_doc_count,
        },
    )