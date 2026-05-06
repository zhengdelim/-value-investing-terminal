import json
import hashlib
from typing import Any, Optional
from ..database import redis_client
from ..config import get_settings

settings = get_settings()


def _key(prefix: str, **kwargs) -> str:
    payload = json.dumps(kwargs, sort_keys=True)
    h = hashlib.md5(payload.encode()).hexdigest()[:8]
    return f"vs:{prefix}:{h}"


def cache_get(key: str) -> Optional[Any]:
    raw = redis_client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    ttl = ttl or settings.cache_ttl
    redis_client.setex(key, ttl, json.dumps(value, default=str))


def cache_delete(key: str) -> None:
    redis_client.delete(key)


def cache_delete_many(*keys: str) -> None:
    if keys:
        redis_client.delete(*keys)


def make_key(prefix: str, **kwargs) -> str:
    return _key(prefix, **kwargs)
