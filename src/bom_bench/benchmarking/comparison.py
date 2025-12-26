"""SBOM comparison logic using PURLs.

This module handles:
- Loading expected and actual SBOMs
- Extracting and normalizing PURLs from CycloneDX format
- Comparing PURL sets for benchmark metrics
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from packageurl import PackageURL

from bom_bench.logging_config import get_logger

logger = get_logger(__name__)


def normalize_purl(purl_string: str) -> str:
    """Normalize PURL for comparison.

    Normalization includes:
    - Lowercase package names for PyPI packages
    - Underscore to hyphen conversion for PyPI packages
    - Removing qualifiers (they don't affect package identity)

    Args:
        purl_string: Package URL string to normalize

    Returns:
        Normalized PURL string

    Raises:
        ValueError: If the PURL is invalid
    """
    purl = PackageURL.from_string(purl_string)

    # Normalize PyPI packages: lowercase, underscore→hyphen
    name = purl.name
    if purl.type == "pypi":
        name = purl.name.lower().replace("_", "-")

    # Reconstruct without qualifiers for comparison
    # We only compare type/namespace/name/version
    return f"pkg:{purl.type}/{name}@{purl.version}"


def extract_purls_from_cyclonedx(sbom: Dict[str, Any]) -> Set[str]:
    """Extract normalized PURLs from CycloneDX SBOM.

    Args:
        sbom: CycloneDX SBOM dictionary

    Returns:
        Set of normalized PURL strings
    """
    purls = set()

    components = sbom.get("components", [])
    for component in components:
        purl = component.get("purl")
        if purl:
            try:
                normalized = normalize_purl(purl)
                purls.add(normalized)
            except Exception as e:
                logger.debug(f"Skipping invalid PURL '{purl}': {e}")

    return purls


def load_expected_sbom(path: Path) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Load expected SBOM from bom-bench output.

    Expected SBOMs have a wrapper format:
    {
        "satisfiable": true/false,
        "sbom": { ... CycloneDX SBOM ... }
    }

    Args:
        path: Path to expected SBOM JSON file

    Returns:
        Tuple of (sbom_dict or None, satisfiable boolean)
        If loading fails, returns (None, True)
    """
    try:
        with open(path) as f:
            data = json.load(f)

        satisfiable = data.get("satisfiable", True)
        sbom = data.get("sbom")

        if not sbom and satisfiable:
            logger.warning(f"Expected SBOM at {path} has no 'sbom' field")

        return sbom, satisfiable

    except FileNotFoundError:
        logger.debug(f"Expected SBOM not found: {path}")
        return None, True

    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in expected SBOM {path}: {e}")
        return None, True

    except Exception as e:
        logger.warning(f"Error loading expected SBOM {path}: {e}")
        return None, True


def load_actual_sbom(path: Path) -> Optional[Dict[str, Any]]:
    """Load actual SBOM from SCA tool output.

    Actual SBOMs are raw CycloneDX format (no wrapper).

    Args:
        path: Path to actual SBOM JSON file

    Returns:
        SBOM dictionary or None if loading fails
    """
    try:
        with open(path) as f:
            return json.load(f)

    except FileNotFoundError:
        logger.debug(f"Actual SBOM not found: {path}")
        return None

    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in actual SBOM {path}: {e}")
        return None

    except Exception as e:
        logger.warning(f"Error loading actual SBOM {path}: {e}")
        return None


def compare_sboms(
    expected_path: Path,
    actual_path: Path
) -> Tuple[Set[str], Set[str], bool]:
    """Compare expected and actual SBOMs.

    Args:
        expected_path: Path to expected SBOM (bom-bench format)
        actual_path: Path to actual SBOM (raw CycloneDX)

    Returns:
        Tuple of (expected_purls, actual_purls, satisfiable)
        If either SBOM fails to load, returns empty sets.
    """
    # Load expected SBOM
    expected_sbom, satisfiable = load_expected_sbom(expected_path)
    if expected_sbom is None:
        if not satisfiable:
            # Unsatisfiable scenario - expected to have no packages
            return set(), set(), False
        return set(), set(), True

    # Load actual SBOM
    actual_sbom = load_actual_sbom(actual_path)
    if actual_sbom is None:
        return set(), set(), satisfiable

    # Extract PURLs
    expected_purls = extract_purls_from_cyclonedx(expected_sbom)
    actual_purls = extract_purls_from_cyclonedx(actual_sbom)

    return expected_purls, actual_purls, satisfiable
