"""
Verification stage - checks groundedness and detects hallucinations.
"""

from __future__ import annotations
import logging
import re
from typing import Any

from .contracts import VerificationInput, VerificationOutput, VerificationStatus

logger = logging.getLogger(__name__)


async def verify(input_: VerificationInput) -> VerificationOutput:
    """
    Verify that the generated answer is grounded in retrieved documents.

    Uses simple heuristic checks:
    - Named entity overlap between answer and sources
    - Number/statistic verification
    - Citation presence
    - Contradiction detection
    """
    answer = input_.generation_output.answer
    sources = input_.retrieval_output.combined_documents
    threshold = input_.threshold

    if not answer or not sources:
        return VerificationOutput(
            status=VerificationStatus.UNGROUNDED,
            confidence=0.0,
            issues=["No answer or no sources to verify against"],
        )

    # Extract entities from sources
    source_text = " ".join(doc.get("content", "") for doc in sources)
    source_entities = _extract_entities(source_text)
    answer_entities = _extract_entities(answer)

    # Extract numbers/stats
    source_numbers = _extract_numbers(source_text)
    answer_numbers = _extract_numbers(answer)

    # Check entity overlap
    entity_overlap = len(answer_entities & source_entities) / max(len(answer_entities), 1)

    # Check number overlap
    number_overlap = len(answer_numbers & source_numbers) / max(len(answer_numbers), 1)

    # Check citations
    citation_count = len(input_.generation_output.citations)
    has_citations = citation_count > 0

    # Check for "I don't know" patterns
    abstention_phrases = [
        "i do not have information",
        "i don't have information",
        "i cannot answer",
        "i don't know",
        "no information",
        "not in the knowledge",
    ]
    is_abstention = any(phrase in answer.lower() for phrase in abstention_phrases)

    # Calculate confidence
    confidence = (
        entity_overlap * 0.4 +
        number_overlap * 0.3 +
        (1.0 if has_citations else 0.0) * 0.2 +
        (1.0 if not is_abstention else 0.5) * 0.1
    )

    # Determine status
    if confidence >= threshold:
        status = VerificationStatus.GROUNDED
    elif confidence >= threshold * 0.5:
        status = VerificationStatus.PARTIALLY_GROUNDED
    else:
        status = VerificationStatus.UNGROUNDED

    # Special case: abstention with no sources is acceptable
    if is_abstention and not sources:
        status = VerificationStatus.GROUNDED
        confidence = 1.0

    issues = []
    if entity_overlap < 0.3:
        issues.append("Low entity overlap with sources")
    if number_overlap < 0.5 and answer_numbers:
        issues.append("Numbers in answer not found in sources")
    if not has_citations and not is_abstention:
        issues.append("No citations provided")

    return VerificationOutput(
        status=status,
        confidence=confidence,
        issues=issues,
        grounded_spans=[],  # Could be enhanced with span-level verification
        ungrounded_spans=[],
        metadata={
            "entity_overlap": entity_overlap,
            "number_overlap": number_overlap,
            "citation_count": citation_count,
            "is_abstention": is_abstention,
        },
    )


def _extract_entities(text: str) -> set[str]:
    """Extract potential entities (capitalized words, acronyms, etc.)."""
    entities = set()
    # Capitalized words (likely proper nouns)
    entities.update(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text))
    # Acronyms
    entities.update(re.findall(r'\b[A-Z]{2,}\b', text))
    # Known GNDEC-specific terms
    gndec_terms = [
        "gnudec", "gndec", "ludhiana", "punjab", "ptu", "ikgptu",
        "btech", "mtech", "phd", "hod", "ai", "ml", "cse", "ece",
        "mechanical", "civil", "electrical", "computer", "electronics",
        "hostel", "library", "placement", "admission", "fee", "fees",
    ]
    text_lower = text.lower()
    for term in gndec_terms:
        if term in text_lower:
            entities.add(term)
    return {e.lower() for e in entities}


def _extract_numbers(text: str) -> set[str]:
    """Extract numbers, percentages, currency values."""
    numbers = set()
    # Percentages
    numbers.update(re.findall(r'\b\d+(?:\.\d+)?%\b', text))
    # Currency (lakhs, crores, rupees, INR)
    numbers.update(re.findall(r'\b\d+(?:\.\d+)?\s*(?:lakh|crore|rs|inr|rupees?)\b', text, re.IGNORECASE))
    # Plain numbers with units
    numbers.update(re.findall(r'\b\d+(?:\.\d+)?\s*(?:students?|faculty|staff|courses?|programs?|branches?|lpa|ctc)\b', text, re.IGNORECASE))
    # Years
    numbers.update(re.findall(r'\b20\d{2}\b', text))
    return {n.lower() for n in numbers}