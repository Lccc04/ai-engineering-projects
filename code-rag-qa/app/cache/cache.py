"""
缓存层 — 基于 dict + TTL 的简单缓存
相同问题直接返回缓存结果，降低 API 成本和延迟
"""
import hashlib
import time
import threading
from app.core.config import settings


class TTLCache:
    """
    带 TTL 的内存缓存

    特点:
    - 线程安全（RLock）
    - 自动过期清理
    - 命中率统计
    """

    def __init__(self, ttl: int | None = None):
        self.ttl = ttl or settings.cache_ttl
        self._store: dict[str, dict] = {}  # key → {value, expire_at}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> dict | None:
        """获取缓存值"""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None

            if time.time() > entry["expire_at"]:
                del self._store[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry["value"]

    def set(self, key: str, value: dict):
        """设置缓存"""
        with self._lock:
            self._store[key] = {
                "value": value,
                "expire_at": time.time() + self.ttl,
            }

    def clear_expired(self):
        """清理过期条目"""
        with self._lock:
            now = time.time()
            expired = [k for k, v in self._store.items() if now > v["expire_at"]]
            for k in expired:
                del self._store[k]

    @property
    def size(self) -> int:
        return len(self._store)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses


# 全局缓存单例
cache = TTLCache()


def cache_key(query: str, mode: str) -> str:
    """生成查询缓存键"""
    raw = f"{query}|{mode}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
