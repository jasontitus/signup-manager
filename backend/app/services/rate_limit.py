"""In-memory failed-attempt throttling for credential endpoints.

Tracks *failed* attempts per key (e.g. client IP + username). After
MAX_FAILURES failures within WINDOW_SECONDS, further attempts are
rejected until the window expires. A successful attempt clears the
counter, so legitimate users are never throttled.

This is process-local, which matches the single-process uvicorn
deployment. If the app is ever scaled to multiple workers, move this
state to a shared store (or enforce limits at the reverse proxy).
"""

import threading
import time
from collections import defaultdict, deque


class FailedAttemptLimiter:
    def __init__(self, max_failures: int = 5, window_seconds: int = 900):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> None:
        q = self._failures[key]
        cutoff = now - self.window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        if not q:
            self._failures.pop(key, None)

    def is_blocked(self, key: str) -> bool:
        """True if the key has exhausted its failure budget."""
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            q = self._failures.get(key)
            return bool(q) and len(q) >= self.max_failures

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._failures[key].append(now)

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        """Clear all state (used by tests)."""
        with self._lock:
            self._failures.clear()


# One limiter per protected endpoint
login_limiter = FailedAttemptLimiter(max_failures=5, window_seconds=900)
unlock_limiter = FailedAttemptLimiter(max_failures=5, window_seconds=900)
