"""Shared logger factory.

Kept at backend root (not under src/) since it's a cross-cutting utility
used by both src/ code and any top-level scripts, matching the import
style `from utils.logger import get_logger` used throughout the codebase.
"""
import logging
import sys

_CONFIGURED = False


def _configure_root_logger() -> None:
    """Attach a stdout handler to the root logger, exactly once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
    )
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    _CONFIGURED = True


def get_logger(
    name: str = "llm_observability_demo",
) -> logging.Logger:
    """Return a configured logger for the given name.

    Args:
        name: The logger name, typically the module using it.

    Returns:
        A logging.Logger instance with the shared stdout handler
        attached (attached lazily, once, on first call).
    """
    _configure_root_logger()
    return logging.getLogger(name)
