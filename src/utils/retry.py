# -*- coding: utf-8 -*-
import functools
import time
from typing import Callable, TypeVar

from src.logger import get_logger

log = get_logger(__name__)
T = TypeVar("T")


def with_retry(max_attempts: int = 3, base_delay: float = 1.0):
    """
    Retry decorator với exponential backoff.
    Delay: 1s → 2s → 4s (với base_delay=1.0)

    Usage:
        @with_retry(max_attempts=3, base_delay=1.0)
        def flaky_network_call(): ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        log.warning(
                            "%s failed (attempt %d/%d) — retrying in %.1fs: %s",
                            func.__name__, attempt, max_attempts, delay, exc,
                        )
                        time.sleep(delay)
            raise last_exc  # type: ignore
        return wrapper
    return decorator
