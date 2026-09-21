import logging

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import AppError
from app.deps.redis import get_redis

logger = logging.getLogger(__name__)


async def rate_limit_auth(request: Request) -> None:
    key = f"rl:auth:{request.client.host if request.client else 'unknown'}"
    try:
        redis = await get_redis()
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, 60)
        if current > 20:
            raise AppError("RATE_LIMITED", "Слишком много попыток", http_status=429)
    except AppError:
        raise
    except Exception:
        if settings.is_production:
            logger.warning("Rate limiter unavailable")
        return
