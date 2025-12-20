#!/usr/bin/env python3
"""Backwards-compatible entry point for bom-bench.

This file maintains compatibility with existing workflows:
    uv run main.py
    uv run main.py --lock

The implementation has been moved to src/bom_bench/cli.py.
For new usage, prefer:
    uv run bom-bench
    python -m bom_bench
"""

import sys
from bom_bench.cli import main

if __name__ == "__main__":
    sys.exit(main())
