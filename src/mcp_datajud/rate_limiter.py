from __future__ import annotations

import threading
import time
from typing import Optional


class TokenBucketRateLimiter:
    def __init__(
        self,
        rate_per_second: float = 5.0,
        burst_capacity: int = 10,
    ) -> None:
        self.rate_per_second = max(rate_per_second, 0.001)
        self.capacity = max(burst_capacity, 1)
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        deadline = time.monotonic() + timeout if timeout is not None else None
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
            # Não há tokens suficientes
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(1.0 / self.rate_per_second)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        add_tokens = elapsed * self.rate_per_second
        self._tokens = min(self.capacity, self._tokens + add_tokens)
        self._last_refill = now
