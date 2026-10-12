"""
backend/web_search.py
=====================
SerpAPI-based live web search for current GNDEC data.

When SERP_ALWAYS_SEARCH=true (recommended), a Google search restricted to GNDEC
domains is performed on EVERY query and the live results are merged with FAISS/BM25
results before being sent to the LLM.  This gives the LLM both:
  • Indexed knowledge  (FAISS — fast, structured, comprehensive)
  • Live website data  (SerpAPI — always current, catches new notices/results/fees)

When SERP_ALWAYS_SEARCH=false, web search is only triggered as a fallback when:
  1. FAISS returns fewer documents than SERP_FALLBACK_THRESHOLD, OR
  2. The query contains a live-data keyword (latest, 2025, notice, etc.)

All configuration is read from environment variables — nothing is hardcoded.
"""

import os
import re
import logging
import asyncio
from urllib.parse import urlparse
from typing import Optional
from dotenv import load_dotenv

# Ensure .env is loaded with high priority
load_dotenv(override=True)

logger = logging.getLogger(__name__)

def is_gndec_domain(url: str) -> bool:
    """Validate that the URL belongs strictly to gndec.ac.in or its nested subdomains."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or parsed.path).lower().split(":")[0].strip()
        if host.startswith("www."):
            host = host[4:]
        return host == "gndec.ac.in" or host.endswith(".gndec.ac.in")
    except Exception:
        return False

def get_serpapi_key() -> Optional[str]:
    return os.getenv("SERPAPI_KEY")

def is_always_search() -> bool:
    return os.getenv("SERP_ALWAYS_SEARCH", "true").strip().lower() == "true"

def get_site_restrict() -> str:
    return os.getenv("SERP_SITE_RESTRICT", "site:gndec.ac.in")

def get_max_results() -> int:
    return int(os.getenv("SERP_MAX_RESULTS", "5"))

def get_fallback_threshold() -> int:
    return int(os.getenv("SERP_FALLBACK_THRESHOLD", "2"))

def get_trigger_keywords() -> list[str]:
    return [
        kw.strip().lower()
        for kw in os.getenv(
            "SERP_TRIGGER_KEYWORDS",
            "latest,recent,current,today,new,2024,2025,2026,notice,circular,result,exam date,schedule,announcement"
        ).split(",")
        if kw.strip()
    ]

def get_engine() -> str:
    return os.getenv("SERP_ENGINE", "google")

logger.info(
    f"[WebSearch] Initialised | available={bool(get_serpapi_key())} | "
    f"always_search={is_always_search()} | max_results={get_max_results()}"
)


def is_available() -> bool:
    """Returns True if SERPAPI_KEY is configured."""
    return bool(get_serpapi_key())


def should_trigger_web_search(query: str, faiss_doc_count: int) -> bool:
    """
    Decide whether to call SerpAPI for this query.

    Always returns True when SERP_ALWAYS_SEARCH=true (and key is set).
    Otherwise triggers when:
      1. FAISS returned fewer documents than SERP_FALLBACK_THRESHOLD, OR
      2. The query contains a live-data keyword (latest, recent, 2025, etc.)
    """
    if not is_available():
        return False

    # Always-on mode: run on every single query
    if is_always_search():
        logger.info(f"[WebSearch] SERP_ALWAYS_SEARCH=true → running web search for query")
        return True

    # Fallback mode: check keywords and doc count
    query_lower = query.lower()
    has_live_keyword = any(kw in query_lower for kw in get_trigger_keywords())

    if has_live_keyword:
        logger.info(f"[WebSearch] Live-data keyword detected → triggering SerpAPI")
        return True

    if faiss_doc_count < get_fallback_threshold():
        logger.info(
            f"[WebSearch] FAISS returned only {faiss_doc_count} docs "
            f"(< threshold {get_fallback_threshold()}) → triggering SerpAPI fallback"
        )
        return True

    return False


def clean_web_query(query: str) -> str:
    """Clean conversational filler words to maximize SerpAPI Google search hits."""
    cleaned = re.sub(
        r"(?i)\b(i want( to know)?|tell me( about)?|what is( the)?|which|who is( the)?|how to|give me( the)?|list of( all( the)?)?|can you tell me|please tell me|show me)\b",
        " ",
        query
    )
    words = [w for w in cleaned.split() if w.strip()]
    return " ".join(words) if words else query.strip()


async def search_gndec(query: str) -> list[dict]:
    """
    Search GNDEC websites via SerpAPI and return structured results.

    Each result is a dict with keys:
        - content  : snippet text
        - url      : source URL
        - title    : page title
        - source_file: "web_search" (marks it as live data for the LLM)

    Returns an empty list if SERPAPI_KEY is not set or if search fails.
    """
    api_key = get_serpapi_key()
    if not api_key:
        logger.warning("[WebSearch] SERPAPI_KEY not set — skipping web search")
        return []

    cleaned = clean_web_query(query)
    # Restrict search strictly to GNDEC domains
    full_query = f"{cleaned} {get_site_restrict()}"

    logger.info(f"[WebSearch] SerpAPI search: {full_query!r}")

    try:
        # Run the blocking SerpAPI call in a thread pool to avoid blocking the event loop
        results = await asyncio.to_thread(_fetch_serpapi, full_query)
        if not results:
            fallback_query = f"GNDEC {cleaned} site:gndec.ac.in"
            logger.info(f"[WebSearch] Retrying with strictly site-restricted fallback: {fallback_query!r}")
            results = await asyncio.to_thread(_fetch_serpapi, fallback_query)

        logger.info(f"[WebSearch] Got {len(results)} verified GNDEC results from SerpAPI")
        return results

    except Exception as e:
        logger.error(f"[WebSearch] SerpAPI search failed: {e}")
        return []


def _fetch_serpapi(query: str) -> list[dict]:
    """
    Blocking SerpAPI call. Runs inside a thread pool via asyncio.to_thread.
    Enforces strict domain validation: only URLs belonging to gndec.ac.in or its
    subdomains are admitted into the pipeline.
    """
    from serpapi import GoogleSearch  # type: ignore

    api_key = get_serpapi_key()
    max_results = get_max_results()
    engine = get_engine()

    params = {
        "q": query,
        "api_key": api_key,
        "engine": engine,
        "num": max_results,
        "hl": "en",
        "gl": "in",          # India region for better GNDEC results
        "safe": "active",
    }

    search = GoogleSearch(params)
    data = search.get_dict()

    results = []

    # Organic search results (main body results)
    for item in data.get("organic_results", []):
        snippet = item.get("snippet", "").strip()
        title = item.get("title", "").strip()
        url = item.get("link", "").strip()

        if not snippet:
            continue

        # Strict domain guardrail: only allow gndec.ac.in and its nested subdomains
        if not is_gndec_domain(url):
            logger.debug(f"[WebSearch] Ignored non-GNDEC organic result from external domain: {url}")
            continue

        results.append({
            "content": f"[WEB] {title}: {snippet}",
            "url": url,
            "title": title,
            "source_file": "web_search",
            "metadata": {
                "url": url,
                "title": title,
                "source": "serpapi",
                "section": "Live Web Search",
                "is_live": True,
            },
        })
        if len(results) >= max_results:
            break

    # Knowledge graph result (only if associated with verified GNDEC domain or college title)
    knowledge = data.get("knowledge_graph", {})
    if knowledge:
        kg_desc = knowledge.get("description", "")
        kg_title = knowledge.get("title", "GNDEC")
        kg_url = knowledge.get("website", "")
        if kg_desc and (is_gndec_domain(kg_url) or "guru nanak dev engineering college" in kg_title.lower() or "gndec" in kg_title.lower()):
            valid_url = kg_url if is_gndec_domain(kg_url) else "https://gndec.ac.in"
            results.insert(0, {
                "content": f"[WEB-KNOWLEDGE] {kg_title}: {kg_desc}",
                "url": valid_url,
                "title": kg_title,
                "source_file": "web_search",
                "metadata": {
                    "url": valid_url,
                    "title": kg_title,
                    "source": "serpapi_knowledge_graph",
                    "section": "Live Web Search",
                    "is_live": True,
                },
            })

    # Answer box (e.g., Google featured snippet) - only if link belongs to GNDEC
    answer_box = data.get("answer_box", {})
    if answer_box:
        ab_text = answer_box.get("answer") or answer_box.get("snippet", "")
        ab_title = answer_box.get("title", "Featured Answer")
        ab_url = answer_box.get("link", "")
        if ab_text and (is_gndec_domain(ab_url) or not ab_url):
            valid_ab_url = ab_url if is_gndec_domain(ab_url) else "https://gndec.ac.in"
            results.insert(0, {
                "content": f"[WEB-ANSWER] {ab_title}: {ab_text}",
                "url": valid_ab_url,
                "title": ab_title,
                "source_file": "web_search",
                "metadata": {
                    "url": valid_ab_url,
                    "title": ab_title,
                    "source": "serpapi_answer_box",
                    "section": "Live Web Search",
                    "is_live": True,
                },
            })

    return results[:max_results]
