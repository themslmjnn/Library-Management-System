from src.core.logging import get_logger
import redis
from src.core.config import settings
from typing import Optional, Any
import json

logger = get_logger(__name__)

redis_client = redis.asyncio.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD or None,
    db=settings.REDIS_DB,
    decode_responses=True,
)

async def get_cache(key: str) -> Optional[Any]:
    try:
        value = await redis_client.get(key)

        if value is None:
            return None
        
        return json.loads(value)
    except Exception as e:
        logger.warning(
            "cache_get_failed", 
            key=key, 
            error=str(e),
        )

        return None
    

async def set_cache(key: str, value: Any, ttl_seconds: int = 60) -> None:
    try:
        await redis_client.setex(key, ttl_seconds, json.dumps(value))
    except Exception as e:
        logger.warning(
            "cache_set_failed", 
            key=key, 
            error=str(e),
        )


async def delete_cache(*keys: str) -> None:
    try:
        if keys:
            await redis_client.delete(*keys)
    except Exception as e:
        logger.warning(
            "cache_get_failed", 
            keys=keys, 
            error=str(e),
        )