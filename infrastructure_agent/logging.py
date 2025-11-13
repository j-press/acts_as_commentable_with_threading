"""Logging helpers for the infrastructure agent."""

from __future__ import annotations

import logging
import logging.handlers
import pathlib
from typing import Optional


def configure_logger(log_path: str | pathlib.Path | None, level: int = logging.INFO) -> logging.Logger:
    """Configure a rotating file logger and return it."""

    logger = logging.getLogger("infrastructure_agent")
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    if log_path:
        path = pathlib.Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.handlers.RotatingFileHandler(path, maxBytes=1024 * 1024, backupCount=5)
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
