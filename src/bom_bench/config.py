"""Configuration constants for bom-bench."""

from pathlib import Path

# Version
__version__ = "0.2.0"

# Directory paths (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
SCENARIOS_DIR = OUTPUT_DIR / "scenarios"
"""Directory for generated scenario projects"""
BENCHMARKS_DIR = OUTPUT_DIR / "benchmarks"
"""Directory for benchmark outputs (actual SBOMs, metrics)"""

# Default data source directories
DEFAULT_PACKSE_DIR = DATA_DIR / "packse"

# Packse configuration
PACKSE_INDEX_URL = "http://127.0.0.1:3141/simple-html"
"""URL for packse test index server"""

# Processing settings
LOCK_TIMEOUT_SECONDS = 120
"""Timeout for lock file generation (2 minutes)"""

# Default package manager
DEFAULT_PACKAGE_MANAGER = "uv"
"""Default package manager to use when none is specified"""

# Default data source
DEFAULT_DATA_SOURCE = "packse"
"""Default data source to use when none is specified"""

# Filter criteria
UNIVERSAL_SCENARIOS_ONLY = True
"""Only process scenarios with universal=true"""

EXCLUDE_NAME_PATTERNS = ["example"]
"""Exclude scenarios whose names contain these patterns"""


# Project metadata
PROJECT_NAME = "project"
"""Fixed project name for generated projects"""

PROJECT_VERSION = "0.1.0"
"""Fixed project version for generated projects"""
