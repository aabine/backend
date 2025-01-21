import json
from typing import Any, Optional
from redis import asyncio as aioredis
from app.core.config import settings
import hashlib
import pickle

class CacheService:
    def __init__(self):
        self.redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        self.default_ttl = 3600  # 1 hour default TTL

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
        try:
            value = await self.redis.get(key)
            if value:
                return pickle.loads(value.encode())
            return None
        except Exception as e:
            print(f"Cache get error: {str(e)}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            serialized_value = pickle.dumps(value)
            await self.redis.set(
                key,
                serialized_value,
                ex=ttl or self.default_ttl
            )
            return True
        except Exception as e:
            print(f"Cache set error: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {str(e)}")
            return False

    async def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache clear pattern error: {str(e)}")
            return False

cache_service = CacheService() 