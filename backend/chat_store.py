# backend/chat_store.py
import asyncio
from .db import pg_execute
import uuid
from typing import Any, List, Mapping
import logging

logger = logging.getLogger(__name__)


async def register_session(phone: str, session_id: str):
    query = """
    INSERT INTO chat_sessions (phone, session_id, is_active, closed_at)
    VALUES (%s, %s, TRUE, NULL)
    ON CONFLICT (phone)
    DO UPDATE
    SET session_id = EXCLUDED.session_id,
        is_active = TRUE,
        closed_at = NULL
    """
    try:
        await asyncio.to_thread(
            pg_execute,
            query,
            (phone, session_id),
        )
    except Exception as e:
        logger.warning(f"Could not register session in Postgres: {e}")


async def save_message(phone: str, session_id: str, role: str, message: str):
    try:
        await register_session(phone, session_id)

        query = """
        INSERT INTO chat_history (phone, session_id, role, message)
        VALUES (%s, %s, %s, %s)
        """
        await asyncio.to_thread(
            pg_execute,
            query,
            (phone, session_id, role, message),
        )
    except Exception as e:
        logger.warning(f"Could not save message in Postgres: {e}")


async def get_session_history(phone: str, session_id: str, limit: int = 50):
    query = """
    SELECT role, message, created_at
    FROM chat_history
    WHERE phone = %s AND session_id = %s
    ORDER BY created_at DESC
    LIMIT %s
    """
    try:
        rows = await asyncio.to_thread(
            pg_execute,
            query,
            (phone, session_id, limit),
            True,  # fetch
        )
        return list(reversed(rows or []))
    except Exception as e:
        logger.warning(f"Could not fetch session history from Postgres: {e}")
        return []


async def list_sessions(phone: str):
    query = """
    WITH saved_sessions AS (
        SELECT session_id, MAX(created_at) AS last_activity
        FROM chat_history
        WHERE phone = %s
        GROUP BY session_id
    ),
    active_session AS (
        SELECT session_id, created_at AS last_activity
        FROM chat_sessions
        WHERE phone = %s
    ),
    combined_sessions AS (
        SELECT * FROM saved_sessions
        UNION ALL
        SELECT * FROM active_session
    ),
    unique_sessions AS (
        SELECT session_id, MAX(last_activity) as last_activity
        FROM combined_sessions
        GROUP BY session_id
    )
    SELECT u.session_id,
           (SELECT message
            FROM chat_history h
            WHERE h.session_id = u.session_id AND h.role = 'user'
            ORDER BY created_at DESC LIMIT 1) as last_question
    FROM unique_sessions u
    ORDER BY u.last_activity DESC NULLS LAST
    """
    try:
        rows = await asyncio.to_thread(
            pg_execute,
            query,
            (phone, phone),
            True,  # fetch
        )

        res = []
        if rows:
            for r in rows:
                q = r["last_question"]
                title = q[:30] + "..." if q and len(q) > 30 else (q or "New Chat")
                res.append({"id": r["session_id"], "title": title})
        return res
    except Exception as e:
        logger.warning(f"Could not list sessions from Postgres: {e}")
        return []


async def get_or_create_session_id(phone: str) -> str | None:
    """
    Returns active session_id for phone.
    Creates a new active session if none exists.
    """

    if not phone:
        return None

    try:
        # 1️⃣ Try to fetch existing active session
        select_query = """
            SELECT session_id
            FROM chat_sessions
            WHERE phone = %s
              AND is_active = TRUE
            LIMIT 1
        """

        rows = await asyncio.to_thread(
            pg_execute,
            select_query,
            (phone,),
            True,  # fetch
        )

        if rows:
            return rows[0]["session_id"]

        # 2️⃣ No active session → create new one
        new_session_id = f"session_{uuid.uuid4().hex}"

        insert_query = """
            INSERT INTO chat_sessions (phone, session_id, is_active)
            VALUES (%s, %s, TRUE)
            ON CONFLICT (phone)
            DO UPDATE
            SET session_id = EXCLUDED.session_id,
                is_active = TRUE
            RETURNING session_id
        """

        rows = await asyncio.to_thread(
            pg_execute,
            insert_query,
            (phone, new_session_id),
            True,
        )

        return rows[0]["session_id"] if rows else None

    except Exception:
        return None


async def close_session_for_phone(phone: str) -> List[str]:
    """
    Marks all active sessions for a phone as inactive.

    Returns:
        List[str]: closed session_ids (empty if none closed)
    """

    logging.info(f"[close_session_for_phone] Called with phone={phone!r}")

    if not phone:
        logging.warning("[close_session_for_phone] ❌ Empty phone provided")
        return []

    update_query = """
        UPDATE chat_sessions
        SET is_active = FALSE,
            closed_at = NOW()
        WHERE phone = %s
          AND is_active = TRUE
        RETURNING session_id
    """

    try:
        logging.info("[close_session_for_phone] Executing UPDATE query...")

        rows: List[Mapping[str, Any]] | None = await asyncio.to_thread(
            pg_execute,
            update_query,
            (phone,),
            True,  # fetch
        )

        if not rows:
            logging.warning("[close_session_for_phone] ⚠️ No active sessions found")
            return []

        session_ids = [row["session_id"] for row in rows]

        logging.info(
            f"[close_session_for_phone] ✅ Closed {len(session_ids)} session(s): "
            f"{session_ids}"
        )

        return session_ids

    except Exception as exc:
        logging.error(
            f"[close_session_for_phone] ❌ Exception while closing sessions: {repr(exc)}"
        )
        logging.exception("close_session_for_phone failed")
        return []


async def close_session_by_id(session_id: str) -> bool:
    if not session_id:
        return False

    try:
        query = """
            UPDATE chat_sessions
            SET is_active = FALSE,
                closed_at = NOW()
            WHERE session_id = %s
              AND is_active = TRUE
        """

        await asyncio.to_thread(
            pg_execute,
            query,
            (session_id,),
            False,
        )

        return True

    except Exception:
        logging.exception("Failed closing session_id=%s", session_id)
        return False
