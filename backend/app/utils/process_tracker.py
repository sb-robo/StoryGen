"""Human-readable process flow logging for API and AI pipeline steps."""

from __future__ import annotations

import inspect
import logging

from app.core.config import settings
from app.utils.operation_progress import NODE_STEP_LABELS


def _caller_logger(*, skip: int = 1) -> logging.Logger:
    frame = inspect.currentframe()
    for _ in range(skip + 1):
        if frame is None:
            break
        frame = frame.f_back
    module = frame.f_globals.get("__name__", "app") if frame else "app"
    return logging.getLogger(module)


def _detail_suffix(**detail: object) -> str:
    if not detail:
        return ""
    return " (" + ", ".join(f"{k}={v}" for k, v in detail.items()) + ")"


def node_label(node_name: str) -> str:
    return NODE_STEP_LABELS.get(node_name, node_name.replace("_", " "))


def track(step: str, **detail: object) -> None:
    """Log a pipeline step from the calling module."""
    _caller_logger(skip=1).info("%s%s", step, _detail_suffix(**detail))


def track_queued(action: str, **detail: object) -> None:
    track(f"queued {action}", **detail)


def track_run(action: str, **detail: object) -> None:
    track(f"run {action}", **detail)


def track_saved(entity: str, **detail: object) -> None:
    track(f"saved {entity}", **detail)


def track_error(
    step: str,
    *,
    exc: BaseException | None = None,
    **detail: object,
) -> None:
    msg = f"{step}{_detail_suffix(**detail)}"
    log = _caller_logger(skip=1)
    if exc is not None:
        log.error("%s: %s", msg, exc, exc_info=settings.DEBUG)
    else:
        log.error(msg)
