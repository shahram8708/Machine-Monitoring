import time
from threading import RLock
from typing import Any, Optional
from config import get_config

_cache: dict[str, tuple[float, Any]] = {}
_lock = RLock()

def _ttl_seconds(ttl: Optional[int]) -> int:
    cfg = get_config()
    return ttl or cfg.CACHE_DEFAULT_TTL_SECONDS


def set_cache(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    expiry = time.time() + _ttl_seconds(ttl_seconds)
    with _lock:
        _cache[key] = (expiry, value)


def get_cache(key: str) -> Optional[Any]:
    with _lock:
        item = _cache.get(key)
        if not item:
            return None
        expiry, value = item
        if expiry < time.time():
            _cache.pop(key, None)
            return None
        return value


def invalidate_cache(key_prefix: str | None = None) -> None:
    with _lock:
        if key_prefix is None:
            _cache.clear()
            return
        for k in list(_cache.keys()):
            if k.startswith(key_prefix):
                _cache.pop(k, None)
