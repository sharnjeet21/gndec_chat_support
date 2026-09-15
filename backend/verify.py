# backend/verify.py
"""
Grounding Verification & Honest Abstention Filter for GNDEC RAG.
Prevents hallucinations on unanswerable/private queries (personal bank accounts, passwords, daily menus)
and verifies factual alignment before returning responses.
"""

import os
import re
import logging
from typing import List, Any, Optional

logger = logging.getLogger(__name__)

# Patterns for queries that ask for private, sensitive, or dynamic unrecorded personal data
SENSITIVE_OR_UNANSWERABLE_PATTERNS = [
    r"\b(private|personal)\s+(bank\s+account|account\s+number|phone\s+number|mobile\s+number|home\s+address|email\s+password|login\s+password)\b",
    r"\b(wifi\s+password|campus\s+wifi\s+password|network\s+password|admin\s+password|root\s+password|security\s+pin|atm\s+pin|hotspot\s+password)\b",
    r"\b(lunch\s+menu|dinner\s+menu|breakfast\s+menu)\b.*?\b(next\s+wednesday|next\s+monday|tomorrow|yesterday|next\s+week)\b",
    r"\b(exact\s+lunch\s+menu|exact\s+dinner\s+menu|daily\s+mess\s+menu\s+on)\b",
    r"\b(cgpa|gpa|marks|score|grade|attendance)\s+(of|for|of\s+student|of\s+roll\s*no)\b",
    r"\b(disciplinary|suspension|expulsion|police\s*case|fir|criminal\s*record)\b",
    r"\b(answer\s*key|question\s*paper\s*leak|exam\s*paper\s*leak)\b",
    r"\b(faculty|teacher|professor)\s+(personal\s*phone|personal\s*mobile|whatsapp\s*number|home\s*address)\b",
]
SENSITIVE_REGEX = re.compile("|".join(SENSITIVE_OR_UNANSWERABLE_PATTERNS), flags=re.IGNORECASE)

ABSTENTION_MESSAGE = (
    "I do not have information about that. For official inquiries and authorized details, "
    "please contact Guru Nanak Dev Engineering College administration directly or visit gndec.ac.in."
)

# Scraper/reasoning leak patterns — LLM sometimes echoes its scratchpad instructions
# in the answer when the retrieved context was thin or during multi-model failover.
LEAK_PATTERNS = [
    re.compile(r"```.*?```", re.IGNORECASE | re.DOTALL),
    re.compile(r"^(?:We need to|We must|We'll answer|Let's craft|Let's answer|I will answer|Thinking Process|Plan:).*?(?=\n-|\n\*|\n\d+\.|\n[A-Z][a-z]+:|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^We need to.*?(?=\n\n|\nAnswer|\n[A-Z][a-z]+:|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^Must cite sources.*?(?=\n\n|\nAnswer|\n[A-Z][a-z]+:|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^The documents are numbered.*?(?=\n\n|\nAnswer|\n[A-Z][a-z]+:|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
    re.compile(r"^The context includes Document \d.*?(?=\n\n|\nAnswer|\n[A-Z][a-z]+:|\Z)", re.IGNORECASE | re.DOTALL | re.MULTILINE),
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


def _extract_numbers_and_entities(text: str) -> dict:
    """
    Extract numerical values, currency amounts, dates, and named entities from text.
    Returns dict with keys: 'numbers', 'currencies', 'dates', 'entities'
    """
    if not text:
        return {"numbers": set(), "currencies": set(), "dates": set(), "entities": set()}

    # Numbers (including commas and decimals)
    numbers = set(re.findall(r'\b(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\b', text))

    # Currency amounts with symbols or words
    currencies = set(re.findall(r'(?:₹|Rs\.?|INR\s*)\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?\b|\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:₹|Rs\.?|INR|lakh|lac|million|crore|LPA)\b', text, re.IGNORECASE))

    # Dates (various formats)
    dates = set(re.findall(r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b', text, re.IGNORECASE))

    # Simple named entities (capitalized phrases, excluding stopwords at start)
    # This is a basic implementation - could be enhanced with NER
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    entities = set()
    stopwords_lower = {"the", "and", "is", "in", "to", "of", "for", "with", "a", "an", "on", "at", "by", "this", "that", "from",
                      "are", "was", "were", "be", "as", "or", "it", "its", "you", "your", "we", "our", "all", "can", "has",
                      "have", "had", "will", "would", "about", "more", "any", "which", "there", "their", "they", "been",
                      "also", "into", "other", "some", "such", "than", "then", "them", "these", "two", "one", "first", "new",
                      "each", "gndec", "guru", "nanak", "engineering", "college", "ludhiana", "official", "here", "following",
                      "details", "information", "including", "available", "provided", "please", "contact", "below"}
    for entity in words:
        if entity.lower() not in stopwords_lower and len(entity) > 1:
            entities.add(entity)

    return {
        "numbers": numbers,
        "currencies": currencies,
        "dates": dates,
        "entities": entities
    }


def _check_numerical_grounding(answer: str, context_text: str) -> bool:
    """
    Check if all numerical values, currency amounts, and dates in answer are supported by context.
    Returns True if all numerical claims are grounded, False otherwise.
    """
    answer_nums = _extract_numbers_and_entities(answer)
    context_nums = _extract_numbers_and_entities(context_text)

    # Check numbers
    unsupported_numbers = answer_nums["numbers"] - context_nums["numbers"]
    # Filter out trivial small numbers (like list items 1,2,3) and years that are likely correct
    unsupported_numbers = {n for n in unsupported_numbers
                          if not (n.isdigit() and int(n) <= 10)  # small ordinals
                          and not (n.isdigit() and len(n) == 4 and 1900 <= int(n) <= 2030)}  # plausible years

    # Check currencies
    unsupported_currencies = answer_nums["currencies"] - context_nums["currencies"]

    # Check dates - be more lenient with dates as they might be referenced differently
    unsupported_dates = set()
    for date in answer_nums["dates"]:
        # Normalize date for comparison (simple approach)
        normalized_date = re.sub(r'[/\-\s]', '', date.lower())
        found = False
        for ctx_date in context_nums["dates"]:
            ctx_normalized = re.sub(r'[/\-\s]', '', ctx_date.lower())
            if normalized_date == ctx_normalized:
                found = True
                break
        if not found:
            unsupported_dates.add(date)

    # Check entities - basic check
    unsupported_entities = answer_nums["entities"] - context_nums["entities"]
    # Filter out very common entities that might be missed
    unsupported_entities = {e for e in unsupported_entities if len(e) > 2}

    total_unsupported = len(unsupported_numbers) + len(unsupported_currencies) + len(unsupported_dates) + len(unsupported_entities)

    if total_unsupported > 0:
        logger.warning(
            f"[NUMERICAL/ENTITY HALLUCINATION] Unsupported: "
            f"numbers={unsupported_numbers}, currencies={unsupported_currencies}, "
            f"dates={unsupported_dates}, entities={unsupported_entities}"
        )
        return False

    return True


STOPWORDS = {
    "the", "and", "is", "in", "to", "of", "for", "with", "a", "an", "on", "at", "by", "this", "that", "from",
    "are", "was", "were", "be", "as", "or", "it", "its", "you", "your", "we", "our", "all", "can", "has",
    "have", "had", "will", "would", "about", "more", "any", "which", "there", "their", "they", "been",
    "also", "into", "other", "some", "such", "than", "then", "them", "these", "two", "one", "first", "new",
    "each", "gndec", "guru", "nanak", "engineering", "college", "ludhiana", "official", "here", "following",
    "details", "information", "including", "available", "provided", "please", "contact", "below",
}


def _extract_tokens(text: str) -> set:
    if not text:
        return set()
    tokens = re.findall(r'[\w਀-੿ऀ-ॿ]{3,}', text.lower())
    return {t for t in tokens if t not in STOPWORDS}


def verify_groundedness(answer: str, context_docs: List[Any], min_overlap_ratio: float = float(os.getenv("VERIFY_MIN_OVERLAP", "0.35"))) -> str:
    """
    Verifies that the generated answer does not introduce unsupported numbers or entities.
    If the context is empty and the answer is not an abstention, falls back to honest refusal.
    """
    if not answer or not answer.strip():
        return ABSTENTION_MESSAGE

    # If already an abstention or standard notice, pass through
    ans_lower = answer.lower()
    abstention_indicators = [
        "i do not have information",
        "only have knowledge about",
        "i can't answer this",
        "cannot answer",
        "not mentioned in the",
        "not available in the",
        "sufficient information",
        "official inquiries and authorized details",
    ]
    if any(phrase in ans_lower for phrase in abstention_indicators):
        return answer

    if not context_docs:
        return ABSTENTION_MESSAGE

    # First, check numerical and entity grounding
    context_text_parts = []
    for doc in context_docs:
        if isinstance(doc, dict):
            context_text_parts.append(str(doc.get("answer", "")))
            context_text_parts.append(str(doc.get("question", "")))
            context_text_parts.append(str(doc.get("text", "")))
            context_text_parts.append(str(doc.get("page_content", "")))
        elif hasattr(doc, "page_content"):
            context_text_parts.append(str(doc.page_content))
            if hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
                context_text_parts.append(str(doc.metadata.get("answer", "")))
                context_text_parts.append(str(doc.metadata.get("question", "")))
        else:
            context_text_parts.append(str(doc))

    context_text = " ".join(context_text_parts)

    if not _check_numerical_grounding(answer, context_text):
        logger.warning("[GROUNDING FAILED] Numerical/entity check failed — Abstaining.")
        return ABSTENTION_MESSAGE

    ans_tokens = _extract_tokens(answer)
    if not ans_tokens or len(ans_tokens) < 3:
        return answer

    # Aggregate context tokens
    ctx_parts = []
    for doc in context_docs:
        if isinstance(doc, dict):
            ctx_parts.append(str(doc.get("answer", "")))
            ctx_parts.append(str(doc.get("question", "")))
            ctx_parts.append(str(doc.get("text", "")))
            ctx_parts.append(str(doc.get("page_content", "")))
        elif hasattr(doc, "page_content"):
            ctx_parts.append(str(doc.page_content))
            if hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
                ctx_parts.append(str(doc.metadata.get("answer", "")))
                ctx_parts.append(str(doc.metadata.get("question", "")))
        else:
            ctx_parts.append(str(doc))

    ctx_text = " ".join(ctx_parts)
    ctx_tokens = _extract_tokens(ctx_text)

    overlap = ans_tokens.intersection(ctx_tokens)
    overlap_ratio = len(overlap) / len(ans_tokens) if ans_tokens else 1.0

    if overlap_ratio < min_overlap_ratio:
        logger.warning(
            f"[GROUNDING FAILED] Overlap ratio {overlap_ratio:.2f} < {min_overlap_ratio:.2f} "
            f"(ans_tokens={len(ans_tokens)}, overlap={len(overlap)}) — Abstaining."
        )
        return ABSTENTION_MESSAGE

    return answer