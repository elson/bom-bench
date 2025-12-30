"""Pytest configuration and fixtures for bom-bench tests."""

import logging

import pytest


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration after each test.

    This ensures that tests which call setup_logging() don't affect
    other tests that rely on caplog fixture for log capture.
    """
    yield

    # Reset the bom_bench logger after test
    logger = logging.getLogger("bom_bench")
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True
