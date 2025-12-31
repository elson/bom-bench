"""SBOM comparison logic using PURLs.

This module handles:
- Loading expected and actual SBOMs
- Extracting and normalizing PURLs from CycloneDX format
- Comparing PURL sets for benchmark metrics
"""

import json
from pathlib import Path
from typing import Any

from packageurl import PackageURL

from bom_bench.config import PROJECT_NAME, PROJECT_VERSION
from bom_bench.logging import get_logger

logger = get_logger(__name__)

# Root project PURL to filter out from comparisons
# SCA tools like Syft include the root project as a component, but it's not a dependency
ROOT_PROJECT_PURL = f"pkg:pypi/{PROJECT_NAME}@{PROJECT_VERSION}"


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


def extract_purls_from_cyclonedx(sbom: dict[str, Any]) -> set[str]:
    """Extract normalized PURLs from CycloneDX SBOM.

    Filters out the root project component (pkg:pypi/project@0.1.0) since
    some SCA tools include it while others don't. Only actual dependencies
    should be compared.

    Args:
        sbom: CycloneDX SBOM dictionary

    Returns:
        Set of normalized PURL strings (excluding root project)
    """
    purls = set()

    components = sbom.get("components", [])
    for component in components:
        purl = component.get("purl")
        if purl:
            try:
                normalized = normalize_purl(purl)
                # Filter out the root project - it's not a dependency
                if normalized != ROOT_PROJECT_PURL:
                    purls.add(normalized)
            except Exception as e:
                logger.debug(f"Skipping invalid PURL '{purl}': {e}")

    return purls


def load_scenario_meta(path: Path) -> dict[str, Any] | None:
    """Load scenario metadata from meta.json.

    Meta file contains:
    {
        "satisfiable": true/false,
        "package_manager_result": {
            "exit_code": int,
            "stdout": str,
            "stderr": str
        }
    }

    Args:
        path: Path to meta.json file

    Returns:
        Dictionary with metadata or None if loading fails
    """
    try:
        with open(path) as f:
            data: dict[str, Any] = json.load(f)
            return data

    except FileNotFoundError:
        logger.debug(f"Meta file not found: {path}")
        return None

    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in meta file {path}: {e}")
        return None

    except Exception as e:
        logger.warning(f"Error loading meta file {path}: {e}")
        return None


def load_expected_sbom(
    path: Path, meta_path: Path | None = None
) -> tuple[dict[str, Any] | None, bool]:
    """Load expected SBOM from bom-bench output.

    Supports two formats:
    1. New format (with meta_path): Pure CycloneDX SBOM, satisfiable from meta.json
    2. Legacy format (no meta_path): Wrapper with satisfiable and sbom fields

    Args:
        path: Path to expected SBOM JSON file
        meta_path: Optional path to meta.json (new format)

    Returns:
        Tuple of (sbom_dict or None, satisfiable boolean)
        If loading fails, returns (None, True)
    """
    # New format: meta.json contains satisfiable, SBOM is pure CycloneDX
    if meta_path is not None:
        meta = load_scenario_meta(meta_path)
        if meta is None:
            return None, True

        satisfiable = meta.get("satisfiable", True)

        if not satisfiable:
            # Unsatisfiable scenario - no SBOM expected
            return None, False

        # Load pure CycloneDX SBOM
        try:
            with open(path) as f:
                sbom = json.load(f)
            return sbom, True

        except FileNotFoundError:
            logger.debug(f"Expected SBOM not found: {path}")
            return None, True

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in expected SBOM {path}: {e}")
            return None, True

        except Exception as e:
            logger.warning(f"Error loading expected SBOM {path}: {e}")
            return None, True

    # Legacy format: wrapper with satisfiable and sbom fields
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


def load_actual_sbom(path: Path) -> dict[str, Any] | None:
    """Load actual SBOM from SCA tool output.

    Actual SBOMs are raw CycloneDX format (no wrapper).

    Args:
        path: Path to actual SBOM JSON file

    Returns:
        SBOM dictionary or None if loading fails
    """
    try:
        with open(path) as f:
            data: dict[str, Any] = json.load(f)
            return data

    except FileNotFoundError:
        logger.debug(f"Actual SBOM not found: {path}")
        return None

    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in actual SBOM {path}: {e}")
        return None

    except Exception as e:
        logger.warning(f"Error loading actual SBOM {path}: {e}")
        return None


def compare_sboms(expected_path: Path, actual_path: Path) -> tuple[set[str], set[str], bool]:
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
