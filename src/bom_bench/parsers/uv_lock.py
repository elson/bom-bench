"""Parser for uv.lock files."""

import tomllib
from pathlib import Path
from typing import List

from bom_bench.models.scenario import ExpectedPackage


def parse_uv_lock(lock_file_path: Path) -> List[ExpectedPackage]:
    """Parse uv.lock file and extract resolved packages.

    Args:
        lock_file_path: Path to uv.lock file

    Returns:
        List of ExpectedPackage objects representing resolved dependencies

    Raises:
        FileNotFoundError: If lock file doesn't exist
        Exception: If parsing fails
    """
    if not lock_file_path.exists():
        raise FileNotFoundError(f"Lock file not found: {lock_file_path}")

    try:
        with open(lock_file_path, "rb") as f:
            lock_data = tomllib.load(f)

        packages = []
        for package in lock_data.get("package", []):
            # Skip the virtual project package
            source = package.get("source", {})
            if source.get("virtual") == ".":
                continue

            name = package.get("name")
            version = package.get("version")

            if name and version:
                packages.append(
                    ExpectedPackage(
                        name=name,
                        version=version
                    )
                )

        return packages

    except Exception as e:
        raise Exception(f"Failed to parse uv.lock file: {e}")
