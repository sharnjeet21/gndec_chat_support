# backend/cache.py
import json
import aioredis

# Single Redis client instance
redis_client = aioredis.from_url(
    "redis://localhost:6379/0", encoding="utf-8", decode_responses=True
)


async def redis_get_session(phone: str, session_id: str, n: int = 50):
    """Get last N messages for this session."""
    key = f"chat:{phone}:{session_id}"
    msgs = await redis_client.lrange(key, -n, -1)
    return [json.loads(m) for m in msgs]
