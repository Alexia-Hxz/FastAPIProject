import logging
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)
_redis_client = None
_redis_available = True


async def get_redis():
    global _redis_client, _redis_available
    if not _redis_available:
        return None
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
            await _redis_client.ping()
        except Exception:
            logger.warning("Redis unavailable — running without token blacklist")
            _redis_available = False
            return None
    return _redis_client
