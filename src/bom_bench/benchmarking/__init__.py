"""SBOM comparison utilities.

This module provides functionality for:
- Loading expected and actual SBOMs
- Extracting and normalizing PURLs from CycloneDX format
- Comparing PURL sets for benchmark metrics
"""

from bom_bench.benchmarking.comparison import (
    compare_sboms,
    extract_purls_from_cyclonedx,
    load_actual_sbom,
    load_expected_sbom,
    normalize_purl,
)

__all__ = [
    "compare_sboms",
    "extract_purls_from_cyclonedx",
    "load_actual_sbom",
    "load_expected_sbom",
    "normalize_purl",
]
