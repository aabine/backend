import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings
import hashlib
import pickle
import logging

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        try:
            self.redis = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=False,  # Changed to False for binary data
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            self.default_ttl = 3600  # 1 hour default TTL
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis = None

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a unique cache key based on the function parameters."""
        # Sort kwargs to ensure consistent key generation
        sorted_items = sorted(kwargs.items())
        # Create a string representation of the parameters
        param_str = json.dumps(sorted_items)
        # Generate a hash of the parameters
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"{prefix}:{param_hash}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis:
            logger.warning("Redis not available, skipping cache get")
            return None
        try:
            value = await self.redis.get(key)
            if value:
                return pickle.loads(value)  # Removed encode() call
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with optional TTL."""
        if not self.redis:
            logger.warning("Redis not available, skipping cache set")
            return False
        try:
            serialized_value = pickle.dumps(value)  # Already returns bytes
            await self.redis.set(
                key,
                serialized_value,
                ex=ttl or self.default_ttl
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.redis:
            logger.warning("Redis not available, skipping cache delete")
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False

    async def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching pattern."""
        if not self.redis:
            logger.warning("Redis not available, skipping cache clear pattern")
            return False
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache clear pattern error: {str(e)}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in cache."""
        if not self.redis:
            logger.warning("Redis not available, skipping increment")
            return None
        try:
            return await self.redis.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {str(e)}")
            return None

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for a key."""
        if not self.redis:
            logger.warning("Redis not available, skipping get_ttl")
            return None
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Cache get_ttl error: {str(e)}")
            return None

cache_service = CacheService() 