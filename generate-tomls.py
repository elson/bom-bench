#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "tomli>=2.0.0",
# ]
# ///

"""
Generate pyproject.toml files from packse scenario TOML files.

This script:
1. Discovers all .toml files in the downloads/ directory
2. Filters for scenarios with universal = true
3. Generates pyproject.toml files in output/{SCENARIO_NAME}/ directories
"""

import sys
import tomli
from pathlib import Path


def generate_pyproject_toml(scenario_data: dict) -> str:
    """
    Generate a pyproject.toml file content from scenario data.

    Args:
        scenario_data: Parsed TOML data from a scenario file

    Returns:
        String content for the pyproject.toml file
    """
    lines = ["[project]"]
    lines.append('name = "project"')
    lines.append('version = "0.1.0"')

    # Add dependencies if present
    root = scenario_data.get("root", {})
    requires = root.get("requires", [])

    if requires:
        lines.append("dependencies = [")
        for req in requires:
            lines.append(f'  "{req}",')
        lines.append("]")
    else:
        lines.append("dependencies = []")

    # Add requires-python if present
    requires_python = root.get("requires_python")
    if requires_python:
        lines.append(f'requires-python = "{requires_python}"')

    # Add tool.uv.required-environments if present
    resolver_options = scenario_data.get("resolver_options", {})
    required_environments = resolver_options.get("required_environments", [])

    if required_environments:
        lines.append("")
        lines.append("[tool.uv]")
        lines.append("required-environments = [")
        for env in required_environments:
            # Use single quotes to avoid issues with double quotes in the environment strings
            lines.append(f"  '{env}',")
        lines.append("]")

    return "\n".join(lines) + "\n"


def process_scenario_file(toml_path: Path, output_base: Path) -> bool:
    """
    Process a single scenario TOML file.

    Args:
        toml_path: Path to the scenario TOML file
        output_base: Base directory for output files

    Returns:
        True if the file was processed, False if skipped
    """
    try:
        # Read and parse the TOML file
        with open(toml_path, "rb") as f:
            scenario_data = tomli.load(f)

        # Check if universal = true
        resolver_options = scenario_data.get("resolver_options", {})
        if not resolver_options.get("universal", False):
            return False

        # Get scenario name
        scenario_name = scenario_data.get("name")
        if not scenario_name:
            print(f"Warning: Scenario at {toml_path} has no name field, skipping")
            return False

        # Generate pyproject.toml content
        pyproject_content = generate_pyproject_toml(scenario_data)

        # Create output directory
        output_dir = output_base / scenario_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write pyproject.toml file
        output_file = output_dir / "pyproject.toml"
        output_file.write_text(pyproject_content)

        print(f"Generated: {output_file}")
        return True

    except Exception as e:
        print(f"Error processing {toml_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point for the script."""
    # Define paths
    downloads_dir = Path("downloads")
    output_dir = Path("output")

    # Check if downloads directory exists
    if not downloads_dir.exists():
        print(f"Error: {downloads_dir} directory not found", file=sys.stderr)
        print("Run: packse fetch --dest downloads --force", file=sys.stderr)
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)

    # Find all TOML files
    toml_files = list(downloads_dir.rglob("*.toml"))

    if not toml_files:
        print(f"Warning: No TOML files found in {downloads_dir}")
        return

    print(f"Found {len(toml_files)} TOML files")

    # Process each TOML file
    processed_count = 0
    skipped_count = 0

    for toml_file in toml_files:
        if process_scenario_file(toml_file, output_dir):
            processed_count += 1
        else:
            skipped_count += 1

    print(f"\nSummary:")
    print(f"  Processed: {processed_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Total: {len(toml_files)}")


if __name__ == "__main__":
    main()
