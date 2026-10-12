"""
Resolution planning stage - determines the strategy for answering the query.
"""

from __future__ import annotations
from .contracts import ResolutionInput, ResolutionOutput, ResolutionStrategy


async def plan(input_: ResolutionInput) -> ResolutionOutput:
    """
    Plan the resolution strategy based on query characteristics.

    Strategies:
    - CACHED: Query matches cached answer
    - SINGLE_HOP: Direct retrieval sufficient
    - MULTI_HOP: Requires multiple retrieval steps
    - DOMAIN_REDIRECT: Redirect to external source
    - ABSTAIN: Cannot answer
    """
    query = input_.query.lower().strip()

    # Check for multi-hop indicators
    multihop_patterns = [
        "hod of the department",
        "head of department",
        "department with highest",
        "department with most",
        "course with most",
        "program with highest",
        "faculty with most",
        "who teaches in",
        "who is the hod",
        "which department",
        "highest placement",
        "most students",
        "most phd",
    ]

    is_multihop = any(pattern in query for pattern in multihop_patterns)

    if is_multihop:
        # Generate sub-queries for multi-hop
        sub_queries = _generate_sub_queries(query)
        return ResolutionOutput(
            strategy=ResolutionStrategy.MULTI_HOP,
            sub_queries=sub_queries,
            reasoning=f"Multi-hop query detected: {query[:50]}...",
        )

    # Check for direct faculty lookup
    faculty_patterns = [
        "hod", "faculty", "professor", "teacher", "staff",
        "phd", "ph.d", "doctorate", "roster", "directory",
    ]

    if any(pattern in query for pattern in faculty_patterns):
        return ResolutionOutput(
            strategy=ResolutionStrategy.SINGLE_HOP,
            sub_queries=[input_.query],
            reasoning="Direct faculty/staff lookup",
        )

    # Check for fee/admission/course queries
    direct_patterns = [
        "fee", "fees", "cost", "tuition",
        "admission", "apply", "eligibility", "cutoff",
        "course", "program", "branch", "btech", "mtech",
        "hostel", "facility", "library", "lab",
        "placement", "package", "salary", "company",
    ]

    if any(pattern in query for pattern in direct_patterns):
        return ResolutionOutput(
            strategy=ResolutionStrategy.SINGLE_HOP,
            sub_queries=[input_.query],
            reasoning="Direct domain query",
        )

    # Default to single hop
    return ResolutionOutput(
        strategy=ResolutionStrategy.SINGLE_HOP,
        sub_queries=[input_.query],
        reasoning="Default single-hop resolution",
    )


def _generate_sub_queries(query: str) -> list[str]:
    """Generate sub-queries for multi-hop questions."""
    query = query.lower()

    # HOD of department with highest X
    if "hod of the department with highest" in query:
        metric = query.split("highest")[-1].strip().rstrip("?")
        return [
            f"Which department has the highest {metric}?",
            f"Who is the HOD of that department?",
        ]

    # Department with most X
    if "department with most" in query:
        metric = query.split("most")[-1].strip().rstrip("?")
        return [
            f"Which department has the most {metric}?",
            f"Who is the HOD of that department?",
        ]

    # Who teaches in department with most X
    if "who teaches in the department" in query and "most" in query:
        metric = query.split("most")[-1].strip().rstrip("?")
        return [
            f"Which department has the most {metric}?",
            f"Which faculty teach in that department?",
        ]

    # Course with most students
    if "course with most" in query or "program with most" in query:
        metric = query.split("most")[-1].strip().rstrip("?")
        return [
            f"Which course has the most {metric}?",
            f"What is the fee for that course?",
        ]

    # Generic multi-hop fallback
    return [
        f"First step: {query}",
        f"Second step: Based on first answer, find specific details",
    ]