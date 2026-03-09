import asyncio
import time
from typing import Awaitable, Callable, Optional, Tuple, TypeVar

T = TypeVar("T")


class CircuitBreaker:
    def __init__(self, threshold: int, cooldown_seconds: float) -> None:
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.open_until: Optional[float] = None

    def record_success(self) -> None:
        self.failure_count = 0
        self.open_until = None

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.threshold:
            self.open_until = time.time() + self.cooldown_seconds

    def is_open(self) -> bool:
        if self.open_until is None:
            return False
        if time.time() >= self.open_until:
            self.open_until = None
            self.failure_count = 0
            return False
        return True


async def run_with_retry(
    func: Callable[[], Awaitable[T]],
    retries: int,
    timeout_seconds: float,
) -> Tuple[Optional[T], Optional[Exception]]:
    attempt = 0
    while True:
        try:
            result = await asyncio.wait_for(func(), timeout=timeout_seconds)
            return result, None
        except Exception as exc:
            if attempt >= retries:
                return None, exc
            attempt += 1
