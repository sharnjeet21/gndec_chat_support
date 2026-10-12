"""
Persistence stage - stores verified answers for audit and potential caching.
"""

from __future__ import annotations
import json
import logging
from typing import Any

from .contracts import PersistenceRecord

logger = logging.getLogger(__name__)


async def persist(record: PersistenceRecord) -> bool:
    """
    Persist the verified answer record.

    Currently stores to PostgreSQL via the existing db module.
    Could be extended to also write to a cache for future retrieval.
    """
    from ..db import pg_execute

    try:
        # Create table if not exists
        await _ensure_table()

        # Insert record
        query = """
        INSERT INTO rag_answers (
            id, query, answer, citations, phone, session_id,
            strategy, verification_status, verification_confidence,
            created_at, metadata
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (id) DO UPDATE SET
            answer = EXCLUDED.answer,
            verification_status = EXCLUDED.verification_status,
            verification_confidence = EXCLUDED.verification_confidence
        """

        pg_execute(query, (
            record.id,
            record.query,
            record.answer,
            json.dumps(record.citations),
            record.phone,
            record.session_id,
            record.strategy.value,
            record.verification_status.value,
            record.verification_confidence,
            record.created_at,
            json.dumps(record.metadata),
        ))

        logger.debug(f"[Persistence] Stored answer for query: {record.query[:50]}...")
        return True

    except Exception as e:
        logger.error(f"[Persistence] Failed to persist record: {e}")
        return False


async def _ensure_table() -> None:
    """Ensure the rag_answers table exists."""
    from ..db import pg_execute

    query = """
    CREATE TABLE IF NOT EXISTS rag_answers (
        id UUID PRIMARY KEY,
        query TEXT NOT NULL,
        answer TEXT NOT NULL,
        citations JSONB,
        phone VARCHAR(20),
        session_id VARCHAR(100),
        strategy VARCHAR(50),
        verification_status VARCHAR(50),
        verification_confidence FLOAT,
        created_at TIMESTAMP DEFAULT NOW(),
        metadata JSONB
    )
    """
    pg_execute(query)


async def get_recent_answers(phone: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get recent answers for a phone number (for debugging/audit)."""
    from ..db import pg_execute

    query = """
    SELECT id, query, answer, citations, strategy, verification_status,
           verification_confidence, created_at, metadata
    FROM rag_answers
    WHERE phone = %s
    ORDER BY created_at DESC
    LIMIT %s
    """
    return pg_execute(query, (phone, limit), fetch=True) or []