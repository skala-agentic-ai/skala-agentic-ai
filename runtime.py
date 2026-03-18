"""Runtime helpers."""
from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def get_logger(run_id: str) -> logging.Logger:
    logger = logging.getLogger(f"pipeline.{run_id}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s run_id=%(run_id)s %(levelname)s %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    class RunIdFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.run_id = run_id
            return True

    has_filter = any(
        getattr(existing, "__class__", None).__name__ == "RunIdFilter"
        for existing in logger.filters
    )
    if not has_filter:
        logger.addFilter(RunIdFilter())
    return logger


def with_timeout(fn: Callable[[], T], timeout_seconds: int) -> T:
    start = time.monotonic()
    result = fn()
    elapsed = time.monotonic() - start
    if elapsed > timeout_seconds:
        raise TimeoutError(f"operation timeout: {elapsed:.2f}s > {timeout_seconds}s")
    return result
