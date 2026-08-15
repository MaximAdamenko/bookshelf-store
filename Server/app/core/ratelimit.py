import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status


class SlidingWindow:
    # In-process and per-worker: two uvicorn workers mean two independent
    # budgets. Honest at this scale; a shared store is the fix if we ever
    # scale out. The account lockout in users is the durable control.
    def __init__(self, limit: int, window_seconds: int):
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()
            if not hits:
                del self._hits[key]          # keeps idle keys from accumulating
                hits = self._hits[key]
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True


def rate_limit(limit: int, window_seconds: int):
    window = SlidingWindow(limit, window_seconds)

    def dependency(request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        if not window.allow(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency
