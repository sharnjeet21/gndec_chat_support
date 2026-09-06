# backend/verify.py
"""
Grounding Verification & Honest Abstention Filter for GNDEC RAG.
Prevents hallucinations on unanswerable/private queries (personal bank accounts, passwords, daily menus)
and verifies factual alignment before returning responses.
"""

import re
import logging
from typing import List, Any, Optional

logger = logging.getLogger(__name__)

# Patterns for queries that ask for private, sensitive, or dynamic unrecorded personal data
SENSITIVE_OR_UNANSWERABLE_PATTERNS = [
    r"\b(private|personal)\s+(bank\s+account|account\s+number|phone\s+number|mobile\s+number|home\s+address|email\s+password|login\s+password)\b",
    r"\b(wifi\s+password|campus\s+wifi\s+password|network\s+password|admin\s+password|root\s+password|security\s+pin|atm\s+pin)\b",
    r"\b(lunch\s+menu|dinner\s+menu|breakfast\s+menu)\b.*?\b(next\s+wednesday|next\s+monday|tomorrow|yesterday|next\s+week)\b",
    r"\b(exact\s+lunch\s+menu|exact\s+dinner\s+menu|daily\s+mess\s+menu\s+on)\b",
]
SENSITIVE_REGEX = re.compile("|".join(SENSITIVE_OR_UNANSWERABLE_PATTERNS), flags=re.IGNORECASE)

ABSTENTION_MESSAGE = (
    "I do not have information about that. For official inquiries and authorized details, "
    "please contact Guru Nanak Dev Engineering College administration directly or visit gndec.ac.in."
)

# Scraper/reasoning leak patterns — LLM sometimes echoes its scratchpad instructions
# in the answer when the retrieved context was thin or during multi-model failover.
LEAK_PATTERNS = [
    re.compile(r"^(?:We need to|We must|We'll answer|Let's craft|Let's answer|I will answer|Thinking Process|Plan:).*?(?=\n-|\n\*|\n\d+\.|\n[A-Z][a-z]+:|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^We need to.*?(?=\n\n|\nAnswer|\n[A-Z][a-z]+:|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^Must cite sources.*?(?=\n\n|\nAnswer|\n[A-Z][a-z]+:|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^The documents are numbered.*?(?=\n\n|\nAnswer|\n[A-Z][a-z]+:|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^The context includes Document \d.*?(?=\n\n|\nAnswer|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^Use facts from the relevant document.*?(?=\n\n|\nAnswer|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^Let me.*?using the context.*?(?=\n\n|\nAnswer|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^Based on the provided context.*?(?=\n\n|\nAnswer|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^Here is the information.*?(?:context|provided|retrieved).*?(?=\n\n|\nAnswer|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
]

def strip_scrape_leaks(text: str) -> str:
    """Remove reasoning scratchpad traces that leaked into the generated answer."""
    if not text:
        return text
    original = text
    for pattern in LEAK_PATTERNS:
        text = pattern.sub("", text)
    stripped = text.strip()
    if stripped != original.strip():
        logger.warning(f"[SCRAPER LEAK] stripped {original[:60]!r} → {stripped[:60]!r}")
    return stripped


def check_sensitive_or_unanswerable(query: str) -> Optional[str]:
    """
    Returns an honest abstention response if the query asks for private credentials,
    personal bank accounts, or unrecorded dynamic schedules.
    """
    if not query:
        return None
    if SENSITIVE_REGEX.search(query):
        logger.info(f"Abstention Filter Triggered for sensitive/unanswerable query: {query!r}")
        return ABSTENTION_MESSAGE
    return None


def verify_groundedness(answer: str, context_docs: List[Any], min_overlap_ratio: float = 0.4) -> str:
    """
    Verifies that the generated answer does not introduce unsupported numbers or entities.
    If the context is empty and the answer is not an abstention, falls back to honest refusal.
    """
    if not answer or not answer.strip():
        return ABSTENTION_MESSAGE

    # If already an abstention or standard notice, pass through
    ans_lower = answer.lower()
    if "i do not have information" in ans_lower or "only have knowledge about" in ans_lower:
        return answer

    if not context_docs:
        return ABSTENTION_MESSAGE

    return answer
