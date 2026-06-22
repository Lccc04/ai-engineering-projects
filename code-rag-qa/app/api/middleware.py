"""
中间件 — QPS 限流 + 请求计时
"""
import time
import threading
from fastapi import Request, HTTPException


class TokenBucket:
    """令牌桶限流器"""

    def __init__(self, rate: float = 10.0, burst: int = 20):
        """
        Args:
            rate: 令牌生成速率（每秒）
            burst: 桶容量（允许突发请求）
        """
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """尝试消费令牌，成功返回 True"""
        with self._lock:
            now = time.time()
            # 补充令牌
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


# 全局令牌桶（10 QPS，突发 20）
_limiter = TokenBucket(rate=10.0, burst=20)


async def rate_limit_middleware(request: Request, call_next):
    """QPS 限流中间件"""
    # /health 不限流
    if request.url.path == "/health":
        return await call_next(request)

    if not _limiter.consume(1):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试")

    return await call_next(request)


class TimerMiddleware:
    """请求计时中间件（纯 ASGI）"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # 非 HTTP 请求直接透传
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()

        async def send_with_timing(message):
            if message["type"] == "http.response.start":
                elapsed_ms = (time.perf_counter() - start) * 1000
                # 注入 X-Response-Time 头
                headers = list(message.get("headers", []))
                headers.append(
                    (b"x-response-time", f"{elapsed_ms:.1f}ms".encode())
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_timing)
