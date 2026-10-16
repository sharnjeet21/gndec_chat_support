"""
Policy evaluation stage - determines if a query should be processed, redirected, or denied.
"""

from __future__ import annotations
from .contracts import PolicyInput, PolicyOutput, PolicyDecision


async def evaluate(input_: PolicyInput) -> PolicyOutput:
    """
    Evaluate query against policy rules.

    Rules:
    - Deny: explicit sensitive content, credentials requests, off-topic
    - Redirect: queries about other institutions
    - Clarify: ambiguous queries that need disambiguation
    - Allow: all other GNDEC-related queries
    """
    query = input_.query.strip().lower()

    # Sensitive content patterns
    sensitive_patterns = [
        "credential", "api key", "secret", "token",
        "ssn", "social security", "credit card", "bank account",
        "personal email", "personal phone number", "private phone number", "personal address",
    ]

    # Only treat 'password' as sensitive if not asking about a self-service or official reset procedure
    is_password_procedural = any(kw in query for kw in ["reset", "change", "forgot", "proforma", "procedure", "form", "letter", "how to", "internet", "wifi"])
    if "password" in query and not is_password_procedural:
        sensitive_patterns.append("password")

    for pattern in sensitive_patterns:
        if pattern in query:
            return PolicyOutput(
                decision=PolicyDecision.DENY,
                reason="I cannot provide or request sensitive personal information.",
            )

    # Off-topic detection (non-GNDEC external institutions, other Guru Nanak colleges, coding, general trivia)
    off_topic_indicators = [
        "iit ", "nit ", "bits ", "vellore", "manipal", "srm ", "amrita ",
        "delhi university", "mumbai university", "anna university",
        "gndu", "guru nanak dev university", "gndpc", "guru nanak dev polytechnic",
        "gndit", "guru nanak dev institute of technology",
        "gniet", "guru nanak institute of engineering",
        "gnit", "guru nanak institute of technology",
        "sgnd khalsa", "sri guru nanak dev khalsa",
        "guru nanak khalsa", "gnkc", "ggn khalsa", "ggnkc",
        "guru nanak college of education", "guru nanak institute of management", "gnim",
        "programming", "coding", "python", "java", "c++", "javascript",
        "homework", "assignment", "exam solution", "write code",
    ]

    has_gndec_context = any(kw in query for kw in ["gndec", "gne", "guru nanak dev engineering college", "guru nanak dev engg college", "ludhiana"])

    for indicator in off_topic_indicators:
        if indicator in query and not has_gndec_context:
            return PolicyOutput(
                decision=PolicyDecision.REDIRECT,
                reason="I am the official information assistant strictly for Guru Nanak Dev Engineering College (GNDEC), Ludhiana. I only provide assistance for GNDEC inquiries.",
                redirect_target="https://gndec.ac.in",
            )

    try:
        from ..domain_guard import is_out_of_domain
        if is_out_of_domain(input_.query):
            return PolicyOutput(
                decision=PolicyDecision.REDIRECT,
                reason="I am the official information assistant strictly for Guru Nanak Dev Engineering College (GNDEC), Ludhiana. I only answer inquiries related to GNDEC.",
                redirect_target="https://gndec.ac.in",
            )
    except Exception:
        pass

    # Ambiguous queries that need clarification
    ambiguous_patterns = [
        "what about", "how about", "and this", "then what",
        "details", "more info", "tell me more",
    ]

    if len(query.split()) <= 2 and any(p in query for p in ambiguous_patterns):
        return PolicyOutput(
            decision=PolicyDecision.CLARIFY,
            reason="Your question is too brief. Could you please provide more details about what you'd like to know regarding GNDEC?",
            clarification_prompt="Please specify what information you're looking for (e.g., admissions, courses, fees, faculty, facilities, placements).",
        )

    # Allow by default for GNDEC queries
    return PolicyOutput(
        decision=PolicyDecision.ALLOW,
        reason="Query is within GNDEC domain.",
    )