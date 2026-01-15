"""Fixture mapper for npm arborist test fixtures."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FixtureMappingEntry:
    """Mapping between fixture name, test name, and saved directory."""

    fixture_name: str
    test_name: str
    saved_dir: Path
    snapshot_prefix: str


def directory_to_test_name(dir_name: str) -> str:
    """Convert directory name to test name.

    Args:
        dir_name: Directory name like 'tap-testdir-reify-link-meta-deps-update'

    Returns:
        Test name like 'link meta deps update'
    """
    # Remove prefix
    name = dir_name.replace("tap-testdir-reify-", "")
    # Replace hyphens with spaces
    return name.replace("-", " ")


def test_name_to_directory(test_name: str) -> str:
    """Convert test name to directory name.

    Args:
        test_name: Test name like 'link meta deps, update'

    Returns:
        Directory name like 'tap-testdir-reify-link-meta-deps-update'
    """
    # Remove commas
    name = test_name.replace(",", "")
    # Replace spaces with hyphens
    name = name.replace(" ", "-")
    # Add prefix
    return f"tap-testdir-reify-{name}"


def sanitize_test_name(test_name: str) -> str:
    """Sanitize test name to match directory naming.

    Args:
        test_name: Test name like 'link meta deps, update'

    Returns:
        Sanitized name like 'link-meta-deps-update'
    """
    # Remove commas
    name = test_name.replace(",", "")
    # Replace spaces with hyphens
    return name.replace(" ", "-")


def build_fixture_mapping(
    snapshot_file: Path, saved_fixtures_dir: Path
) -> dict[str, FixtureMappingEntry]:
    """Build mapping from saved fixture directories to snapshot entries.

    Args:
        snapshot_file: Path to reify.js.test.cjs snapshot file
        saved_fixtures_dir: Path to directory containing tap-testdir-reify-* directories

    Returns:
        Dict mapping fixture name to FixtureMappingEntry
    """
    # Read snapshot file to extract test names
    snapshot_content = snapshot_file.read_text() if snapshot_file.exists() else ""

    # Parse exports to extract test names
    # Format: exports[`test/arborist/reify.js TAP <test_name> > <description>`] = `...`;
    export_pattern = r"exports\[`test/arborist/reify\.js TAP ([^>]+) >"
    snapshot_tests = {}
    for match in re.finditer(export_pattern, snapshot_content):
        test_name = match.group(1).strip()
        # Store the snapshot prefix (everything before >)
        snapshot_prefix = f"test/arborist/reify.js TAP {test_name}"
        snapshot_tests[test_name] = snapshot_prefix

    # Scan directories and match to snapshot entries
    mapping = {}

    if not saved_fixtures_dir.exists():
        return mapping

    for dir_path in saved_fixtures_dir.iterdir():
        if not dir_path.is_dir():
            continue

        dir_name = dir_path.name

        # Only process tap-testdir-reify-* directories
        if not dir_name.startswith("tap-testdir-reify-"):
            continue

        # Convert directory name to test name
        test_name_from_dir = directory_to_test_name(dir_name)

        # Try to match with snapshot entries
        # The test name from directory might not have commas, but snapshot might
        # So we try fuzzy matching
        matched_snapshot_prefix = None
        matched_test_name = None

        for snapshot_test_name, prefix in snapshot_tests.items():
            # Normalize both for comparison (remove commas, extra spaces)
            normalized_snapshot = sanitize_test_name(snapshot_test_name)
            normalized_dir = sanitize_test_name(test_name_from_dir)

            if normalized_snapshot == normalized_dir:
                matched_snapshot_prefix = prefix
                matched_test_name = snapshot_test_name
                break

        # If no match found, use the directory-derived test name
        if matched_snapshot_prefix is None or matched_test_name is None:
            matched_snapshot_prefix = f"test/arborist/reify.js TAP {test_name_from_dir}"
            matched_test_name = test_name_from_dir

        # Create mapping entry
        fixture_name = sanitize_test_name(test_name_from_dir)

        mapping[fixture_name] = FixtureMappingEntry(
            fixture_name=fixture_name,
            test_name=matched_test_name,
            saved_dir=dir_path,
            snapshot_prefix=matched_snapshot_prefix,
        )

    return mapping
