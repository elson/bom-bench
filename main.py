#!/usr/bin/env python3

"""
Generate pyproject.toml files from packse scenarios.

This script:
1. Reads scenario data from scenarios.json
2. Filters for scenarios with universal = true
3. Generates pyproject.toml files in output/{SCENARIO_NAME}/ directories
4. Optionally generates lock files with --lock flag
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def generate_pyproject_toml(scenario: dict) -> str:
    """
    Generate a pyproject.toml file content from scenario data.

    Args:
        scenario: Scenario data from scenarios.json

    Returns:
        String content for the pyproject.toml file
    """
    lines = ["[project]"]
    lines.append('name = "project"')
    lines.append('version = "0.1.0"')

    # Add dependencies if present
    root = scenario.get("root", {})
    requires = root.get("requires", [])

    if requires:
        lines.append("dependencies = [")
        for req_obj in requires:
            # Use the "requirement" field which includes the full package name with scenario prefix
            requirement = req_obj.get("requirement", "")
            # Use single quotes to avoid issues with double quotes in markers
            lines.append(f"  '{requirement}',")
        lines.append("]")
    else:
        lines.append("dependencies = []")

    # Add requires-python if present
    requires_python = root.get("requires_python")
    if requires_python:
        lines.append(f'requires-python = "{requires_python}"')

    # Add tool.uv.required-environments if present
    resolver_options = scenario.get("resolver_options", {})
    required_environments = resolver_options.get("required_environments")

    if required_environments:
        lines.append("")
        lines.append("[tool.uv]")
        lines.append("required-environments = [")
        for env in required_environments:
            # Use single quotes to avoid issues with double quotes in the environment strings
            lines.append(f"  '{env}',")
        lines.append("]")

    return "\n".join(lines) + "\n"


def run_uv_lock(scenario_dir: Path, scenario_name: str) -> tuple[bool, int]:
    """
    Run uv lock for a scenario and capture output.

    Args:
        scenario_dir: Directory containing the pyproject.toml
        scenario_name: Name of the scenario (for logging)

    Returns:
        Tuple of (success: bool, exit_code: int)
    """
    output_file = scenario_dir / "uv-lock-output.txt"

    try:
        # Run uv lock with the specified index URL
        result = subprocess.run(
            ["uv", "lock", "--index-url", "http://127.0.0.1:3141/simple-html"],
            cwd=scenario_dir,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout per lock
        )

        # Write output to file
        with open(output_file, "w") as f:
            f.write(f"Exit code: {result.returncode}\n\n")
            f.write("=== STDOUT ===\n")
            f.write(result.stdout)
            f.write("\n\n=== STDERR ===\n")
            f.write(result.stderr)

        success = result.returncode == 0
        return success, result.returncode

    except subprocess.TimeoutExpired:
        with open(output_file, "w") as f:
            f.write("Exit code: TIMEOUT\n\n")
            f.write("Error: Command timed out after 120 seconds\n")
        print(f"  Timeout: {scenario_name}", file=sys.stderr)
        return False, -1

    except Exception as e:
        with open(output_file, "w") as f:
            f.write(f"Exit code: ERROR\n\n")
            f.write(f"Error: {str(e)}\n")
        print(f"  Error running uv lock for {scenario_name}: {e}", file=sys.stderr)
        return False, -1


def process_scenario(scenario: dict, output_base: Path) -> bool:
    """
    Process a single scenario from scenarios.json.

    Args:
        scenario: Scenario data dictionary
        output_base: Base directory for output files

    Returns:
        True if the scenario was processed, False if skipped
    """
    try:
        # Get scenario name
        scenario_name = scenario.get("name")
        if not scenario_name:
            print("Warning: Scenario has no name field, skipping", file=sys.stderr)
            return False

        # Skip scenarios with "example" in the name
        if "example" in scenario_name.lower():
            return False

        # Check if universal = true
        resolver_options = scenario.get("resolver_options", {})
        if not resolver_options.get("universal", False):
            return False

        # Generate pyproject.toml content
        pyproject_content = generate_pyproject_toml(scenario)

        # Create output directory
        output_dir = output_base / scenario_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write pyproject.toml file
        output_file = output_dir / "pyproject.toml"
        output_file.write_text(pyproject_content)

        print(f"Generated: {output_file}")
        return True

    except Exception as e:
        print(f"Error processing scenario '{scenario.get('name', 'unknown')}': {e}", file=sys.stderr)
        return False


def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate pyproject.toml files from packse scenarios"
    )
    parser.add_argument(
        "--lock",
        action="store_true",
        help="Generate lock files for each scenario using uv lock"
    )
    args = parser.parse_args()

    # Define paths
    scenarios_file = Path("scenarios.json")
    output_dir = Path("output")

    # Check if scenarios.json exists
    if not scenarios_file.exists():
        print(f"Error: {scenarios_file} not found", file=sys.stderr)
        print("Run: packse fetch to generate scenarios.json", file=sys.stderr)
        sys.exit(1)

    # Read and parse scenarios.json
    try:
        with open(scenarios_file) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse {scenarios_file}: {e}", file=sys.stderr)
        sys.exit(1)

    scenarios = data.get("scenarios", [])
    if not scenarios:
        print(f"Warning: No scenarios found in {scenarios_file}")
        return

    print(f"Found {len(scenarios)} scenarios")

    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)

    # Process each scenario
    processed_count = 0
    skipped_count = 0
    processed_scenarios = []

    for scenario in scenarios:
        if process_scenario(scenario, output_dir):
            processed_count += 1
            processed_scenarios.append(scenario)
        else:
            skipped_count += 1

    print(f"\nGeneration Summary:")
    print(f"  Processed: {processed_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Total: {len(scenarios)}")

    # If --lock flag is set, generate lock files
    if args.lock:
        print(f"\nGenerating lock files for {processed_count} scenarios...")
        lock_success = 0
        lock_failure = 0

        for scenario in processed_scenarios:
            scenario_name = scenario["name"]
            scenario_dir = output_dir / scenario_name
            print(f"  Locking: {scenario_name}...", end=" ", flush=True)

            success, exit_code = run_uv_lock(scenario_dir, scenario_name)

            if success:
                print("✓")
                lock_success += 1
            else:
                print(f"✗ (exit code: {exit_code})")
                lock_failure += 1

        print(f"\nLock Summary:")
        print(f"  Success: {lock_success}")
        print(f"  Failed: {lock_failure}")
        print(f"  Total: {processed_count}")


if __name__ == "__main__":
    main()
