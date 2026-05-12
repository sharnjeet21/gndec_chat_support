# backend/db.py
import os
from dotenv import load_dotenv
from psycopg import connect
from psycopg.rows import dict_row

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SESSION_TTL = int(os.getenv("SESSION_TTL", "86400"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

conn = connect(DATABASE_URL, autocommit=True, row_factory=dict_row)


def pg_execute(query: str, params=None, fetch: bool = False):
    with conn.cursor() as cur:
        cur.execute(query, params or ())
        if fetch:
            return cur.fetchall()
        return None
