# backend/chat_store.py
import asyncio
from .db import pg_execute
import uuid
from typing import List
import logging


async def save_message(phone: str, session_id: str, role: str, message: str):
    query = """
    INSERT INTO chat_history (phone, session_id, role, message)
    VALUES (%s, %s, %s, %s)
    """
    await asyncio.to_thread(
        pg_execute,
        query,
        (phone, session_id, role, message),
    )


async def get_session_history(phone: str, session_id: str, limit: int = 50):
    query = """
    SELECT role, message, created_at
    FROM chat_history
    WHERE phone = %s AND session_id = %s
    ORDER BY created_at DESC
    LIMIT %s
    """
    rows = await asyncio.to_thread(
        pg_execute,
        query,
        (phone, session_id, limit),
        True,  # fetch
    )
    return list(reversed(rows or []))


async def list_sessions(phone: str):
    query = """
    SELECT DISTINCT session_id
    FROM chat_history
    WHERE phone = %s
    ORDER BY session_id ASC
    """
    rows = await asyncio.to_thread(
        pg_execute,
        query,
        (phone,),
        True,  # fetch
    )
    return [r["session_id"] for r in rows] if rows else []


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

    print(f"[close_session_for_phone] Called with phone={phone!r}")

    if not phone:
        print("[close_session_for_phone] ❌ Empty phone provided")
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
        print("[close_session_for_phone] Executing UPDATE query...")

        rows: List[Mapping[str, Any]] | None = await asyncio.to_thread(
            pg_execute,
            update_query,
            (phone,),
            True,  # fetch
        )

        if not rows:
            print("[close_session_for_phone] ⚠️ No active sessions found")
            return []

        session_ids = [row["session_id"] for row in rows]

        print(
            f"[close_session_for_phone] ✅ Closed {len(session_ids)} session(s): "
            f"{session_ids}"
        )

        return session_ids

    except Exception as exc:
        print(
            "[close_session_for_phone] ❌ Exception while closing sessions:",
            repr(exc),
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
