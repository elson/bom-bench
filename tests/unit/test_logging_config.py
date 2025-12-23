"""Tests for logging configuration."""

import logging

from bom_bench.logging_config import setup_logging, get_logger, LOGGER_NAME


class TestLoggingConfiguration:
    """Test logging setup and configuration."""

    def test_default_log_level(self):
        """Test that default log level is INFO."""
        setup_logging()
        # Check the package-level logger
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.level == logging.INFO

    def test_verbose_flag(self):
        """Test that verbose flag sets DEBUG level."""
        setup_logging(verbose=True)
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.level == logging.DEBUG

    def test_quiet_flag(self):
        """Test that quiet flag sets WARNING level."""
        setup_logging(quiet=True)
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.level == logging.WARNING

    def test_explicit_log_level(self):
        """Test explicit log level setting."""
        setup_logging(log_level="ERROR")
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.level == logging.ERROR

    def test_log_level_overrides_verbose(self):
        """Test that explicit log level overrides verbose flag."""
        setup_logging(verbose=True, log_level="WARNING")
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.level == logging.WARNING

    def test_log_level_overrides_quiet(self):
        """Test that explicit log level overrides quiet flag."""
        setup_logging(quiet=True, log_level="DEBUG")
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.level == logging.DEBUG

    def test_get_logger_with_module_name(self):
        """Test getting logger with module name."""
        logger = get_logger("test_module")
        assert logger.name == f"{LOGGER_NAME}.test_module"

    def test_get_logger_preserves_full_name(self):
        """Test that get_logger preserves names that already start with package name."""
        full_name = f"{LOGGER_NAME}.submodule"
        logger = get_logger(full_name)
        assert logger.name == full_name
