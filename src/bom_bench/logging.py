"""Logging configuration for bom-bench."""

import logging

from rich.logging import RichHandler

from bom_bench.console import console

LOGGER_NAME = "bom_bench"


def setup_logging(verbose: bool = False, quiet: bool = False, log_level: str | None = None) -> None:
    """Configure logging for bom-bench.

    Args:
        verbose: Enable DEBUG level logging
        quiet: Show only WARNING and above
        log_level: Explicit log level (overrides verbose/quiet)
    """
    if log_level:
        level = getattr(logging, log_level.upper())
    elif verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.handlers.clear()

    handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        rich_tracebacks=True,
    )
    handler.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module
    """
    if not name.startswith(LOGGER_NAME):
        name = f"{LOGGER_NAME}.{name}"

    return logging.getLogger(name)
