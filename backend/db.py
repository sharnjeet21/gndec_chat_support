# backend/db.py
import os
import logging
from dotenv import load_dotenv
from psycopg import connect
from psycopg.rows import dict_row

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
SESSION_TTL = int(os.getenv("SESSION_TTL", "86400"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_conn = None


def get_conn():
    global _conn
    if _conn is None or _conn.closed:
        try:
            _conn = connect(DATABASE_URL, autocommit=True, row_factory=dict_row, connect_timeout=2)
        except Exception as e:
            # Fallback to localhost if 'postgres' host failed in local non-docker environment
            if "@postgres:" in (DATABASE_URL or ""):
                local_url = DATABASE_URL.replace("@postgres:", "@localhost:")
                try:
                    _conn = connect(local_url, autocommit=True, row_factory=dict_row, connect_timeout=2)
                    return _conn
                except Exception:
                    pass
            logger.debug(f"PostgreSQL connection unavailable: {e}")
            return None
    return _conn


def pg_execute(query: str, params=None, fetch: bool = False):
    try:
        conn = get_conn()
        if conn is None or conn.closed:
            return [] if fetch else None
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if fetch:
                return cur.fetchall()
            return None
    except Exception as e:
        logger.debug(f"pg_execute failed: {e}")
        return [] if fetch else None
