"""Benchmarking layer for SCA tools.

This module provides functionality for:
- Running SCA tools against generated outputs
- Comparing SCA tool output with expected SBOMs
- Generating comparison reports across tools and package managers
"""

from bom_bench.benchmarking.runner import BenchmarkRunner

__all__ = [
    "BenchmarkRunner",
]
