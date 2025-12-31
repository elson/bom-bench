"""Logging configuration for bom-bench."""

import logging
import sys

import click

# Package-level logger
LOGGER_NAME = "bom_bench"

# Color mapping for log levels
LEVEL_COLORS = {
    "DEBUG": "blue",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red",
}


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output using Click."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors.

        Args:
            record: Log record to format

        Returns:
            Formatted message with color codes
        """
        # Format the base message
        message = super().format(record)

        # Color the level name
        level_color = LEVEL_COLORS.get(record.levelname, "white")

        # For ERROR and CRITICAL, color the entire message
        if record.levelno >= logging.ERROR:
            return click.style(message, fg=level_color, bold=True)
        else:
            return message


def setup_logging(verbose: bool = False, quiet: bool = False, log_level: str | None = None) -> None:
    """Configure logging for bom-bench.

    Args:
        verbose: Enable DEBUG level logging
        quiet: Show only WARNING and above
        log_level: Explicit log level (overrides verbose/quiet)
    """
    # Determine log level: explicit > verbose > quiet > INFO
    if log_level:
        level = getattr(logging, log_level.upper())
    elif verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    # Get root logger for our package
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Create formatter
    formatter = ColoredFormatter(fmt="%(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module
    """
    # Ensure it's under our package namespace
    if not name.startswith(LOGGER_NAME):
        name = f"{LOGGER_NAME}.{name}"

    return logging.getLogger(name)
