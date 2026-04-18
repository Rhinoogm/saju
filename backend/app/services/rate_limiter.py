from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


class InMemoryRateLimiter:
    def __init__(self, *, per_ip_per_hour: int, global_per_minute: int) -> None:
        self.per_ip_per_hour = per_ip_per_hour
        self.global_per_minute = global_per_minute
        self._ip_hits: defaultdict[str, deque[float]] = defaultdict(deque)
        self._global_hits: deque[float] = deque()
        self._lock = asyncio.Lock()

    @staticmethod
    def _prune(hits: deque[float], *, now: float, window_seconds: int) -> None:
        cutoff = now - window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()

    @staticmethod
    def _retry_after(hits: deque[float], *, now: float, window_seconds: int) -> int:
        if not hits:
            return 1
        return max(1, int(hits[0] + window_seconds - now) + 1)

    async def check(self, identifier: str) -> RateLimitResult:
        now = monotonic()
        async with self._lock:
            self._prune(self._global_hits, now=now, window_seconds=60)
            ip_hits = self._ip_hits[identifier]
            self._prune(ip_hits, now=now, window_seconds=3600)

            if self.global_per_minute > 0 and len(self._global_hits) >= self.global_per_minute:
                return RateLimitResult(
                    allowed=False,
                    retry_after_seconds=self._retry_after(self._global_hits, now=now, window_seconds=60),
                )

            if self.per_ip_per_hour > 0 and len(ip_hits) >= self.per_ip_per_hour:
                return RateLimitResult(
                    allowed=False,
                    retry_after_seconds=self._retry_after(ip_hits, now=now, window_seconds=3600),
                )

            self._global_hits.append(now)
            ip_hits.append(now)
            return RateLimitResult(allowed=True)


def client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",", 1)[0].strip()
        if first_ip:
            return first_ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def enforce_llm_rate_limit(request: Request) -> None:
    limiter = getattr(request.app.state, "llm_rate_limiter", None)
    if limiter is None:
        return

    result = await limiter.check(client_identifier(request))
    if result.allowed:
        return

    detail = "무료 공개 데모의 요청 한도에 도달했어요. 잠시 뒤 다시 시도해주세요."
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(result.retry_after_seconds)},
    )
