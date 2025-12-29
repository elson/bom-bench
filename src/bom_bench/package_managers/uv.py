"""UV package manager plugin.

This plugin provides support for the UV Python package manager,
including loading packse scenarios, generating pyproject.toml manifests,
and running uv lock commands.
"""

import shutil
import subprocess
import time
import tomllib
from pathlib import Path
from typing import List, Optional

import packse.fetch
import packse.inspect

from bom_bench.generators.sbom.cyclonedx import generate_sbom_file, generate_meta_file
from bom_bench.logging_config import get_logger
from bom_bench.models.result import LockResult, LockStatus
from bom_bench.models.scenario import Scenario, ExpectedPackage

from bom_bench import hookimpl

logger = get_logger(__name__)

# UV-specific configuration constants
PACKSE_INDEX_URL = "http://127.0.0.1:3141/simple-html"
"""URL for packse test index server"""

LOCK_TIMEOUT_SECONDS = 120
"""Timeout for lock file generation (2 minutes)"""

PROJECT_NAME = "project"
"""Fixed project name for generated projects"""

PROJECT_VERSION = "0.1.0"
"""Fixed project version for generated projects"""


def _generate_pyproject_toml(
    name: str,
    version: str,
    dependencies: List[str],
    requires_python: Optional[str] = None,
    required_environments: Optional[List[str]] = None
) -> str:
    """Generate complete pyproject.toml content for UV.

    Args:
        name: Project name
        version: Project version
        dependencies: List of dependency requirement strings
        requires_python: Python version requirement (e.g., '>=3.12')
        required_environments: List of required environments for universal resolution

    Returns:
        Complete pyproject.toml file content as a string
    """
    lines = []

    # [project] section
    lines.append("[project]")
    lines.append(f'name = "{name}"')
    lines.append(f'version = "{version}"')

    # Add dependencies
    if dependencies:
        lines.append("dependencies = [")
        for dep in dependencies:
            # Use single quotes to avoid issues with double quotes in markers
            lines.append(f"  '{dep}',")
        lines.append("]")
    else:
        lines.append("dependencies = []")

    # Add requires-python if present
    if requires_python:
        lines.append(f'requires-python = "{requires_python}"')

    # [tool.uv] section for required environments
    if required_environments:
        lines.append("")
        lines.append("[tool.uv]")
        lines.append("required-environments = [")
        for env in required_environments:
            # Use single quotes to avoid issues with double quotes in the environment strings
            lines.append(f"  '{env}',")
        lines.append("]")

    return "\n".join(lines) + "\n"


def _parse_uv_lock(lock_file_path: Path) -> List[ExpectedPackage]:
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


def _get_uv_version() -> Optional[str]:
    """Get UV version if installed."""
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Format: "uv 0.5.11"
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                return parts[1]
    except Exception:
        pass
    return None


@hookimpl
def register_package_managers() -> dict:
    """Register UV package manager."""
    return {
        "name": "uv",
        "ecosystem": "python",
        "description": "Fast Python package manager and resolver",
        "data_source": "packse",
        "installed": shutil.which("uv") is not None,
        "version": _get_uv_version()
    }


@hookimpl
def load_scenarios(pm_name: str, data_dir: Path) -> Optional[List[Scenario]]:
    """Load packse scenarios for UV.

    Args:
        pm_name: Package manager name
        data_dir: Base data directory

    Returns:
        List of scenarios, or None if not handled.
    """
    if pm_name != "uv":
        return None

    packse_dir = data_dir / "packse"

    # Fetch if needed
    if not packse_dir.exists():
        logger.info(f"Fetching packse scenarios to {packse_dir}...")
        try:
            if not packse_dir.parent.exists():
                packse_dir.parent.mkdir(parents=True, exist_ok=True)
            packse.fetch.fetch(dest=packse_dir)
            logger.info("Successfully fetched packse scenarios")
        except Exception as e:
            logger.error(f"Failed to fetch packse scenarios: {e}")
            raise

    # Load scenarios
    try:
        scenario_files = list(packse.inspect.find_scenario_files(packse_dir))

        if not scenario_files:
            logger.warning(f"No packse scenario files found in {packse_dir}")
            return []

        template_vars = packse.inspect.variables_for_templates(
            scenario_files,
            no_hash=True
        )

        scenario_dicts = template_vars.get("scenarios", [])

        if not scenario_dicts:
            logger.warning("No scenarios loaded from packse")
            return []

        scenarios = [
            Scenario.from_dict(scenario_dict, source="packse")
            for scenario_dict in scenario_dicts
        ]

        logger.info(f"Loaded {len(scenarios)} packse scenarios")
        return scenarios

    except Exception as e:
        logger.error(f"Failed to load packse scenarios: {e}")
        raise


@hookimpl
def generate_manifest(
    pm_name: str,
    scenario: Scenario,
    output_dir: Path
) -> Optional[Path]:
    """Generate pyproject.toml for UV.

    Args:
        pm_name: Package manager name
        scenario: Scenario to generate manifest for
        output_dir: Scenario output directory

    Returns:
        Path to manifest file, or None if not handled.
    """
    if pm_name != "uv":
        return None

    # Extract dependencies from scenario
    dependencies = [
        req.requirement
        for req in scenario.root.requires
    ]

    # Extract requires-python
    requires_python = scenario.root.requires_python

    # Extract required-environments for universal resolution
    required_environments = scenario.resolver_options.required_environments

    # Generate pyproject.toml content
    content = _generate_pyproject_toml(
        name=PROJECT_NAME,
        version=PROJECT_VERSION,
        dependencies=dependencies,
        requires_python=requires_python,
        required_environments=required_environments if required_environments else None
    )

    # Write to assets subdirectory (keeps project files separate from meta files)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = assets_dir / "pyproject.toml"
    manifest_path.write_text(content)

    return manifest_path


@hookimpl
def run_lock(
    pm_name: str,
    project_dir: Path,
    scenario_name: str,
    timeout: int = LOCK_TIMEOUT_SECONDS
) -> Optional[LockResult]:
    """Execute uv lock command and capture output.

    Args:
        pm_name: Package manager name
        project_dir: Directory containing the pyproject.toml (assets dir)
        scenario_name: Name of the scenario (for logging)
        timeout: Command timeout in seconds

    Returns:
        LockResult with execution details, or None if not handled.
    """
    if pm_name != "uv":
        return None

    lock_file = project_dir / "uv.lock"
    start_time = time.time()

    try:
        # Run uv lock with the packse index URL
        result = subprocess.run(
            ["uv", "lock", "--index-url", PACKSE_INDEX_URL],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duration = time.time() - start_time

        # Determine status
        if result.returncode == 0:
            status = LockStatus.SUCCESS
        else:
            status = LockStatus.FAILED

        return LockResult(
            scenario_name=scenario_name,
            package_manager="uv",
            status=status,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            lock_file=lock_file if lock_file.exists() else None,
            duration_seconds=duration
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time

        logger.warning(f"  Timeout: {scenario_name}")

        return LockResult(
            scenario_name=scenario_name,
            package_manager="uv",
            status=LockStatus.TIMEOUT,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
            error_message=f"Command timed out after {timeout} seconds",
            duration_seconds=duration
        )

    except Exception as e:
        duration = time.time() - start_time

        logger.error(f"  Error running uv lock for {scenario_name}: {e}")

        return LockResult(
            scenario_name=scenario_name,
            package_manager="uv",
            status=LockStatus.ERROR,
            stdout="",
            stderr=str(e),
            error_message=str(e),
            duration_seconds=duration
        )


def _generate_sbom_for_lock_impl(
    scenario: Scenario,
    output_dir: Path,
    lock_result: LockResult
) -> Optional[Path]:
    """Internal implementation for generating SBOM and meta files.

    Generates two files:
    - expected.cdx.json: Pure CycloneDX SBOM (only if lock succeeded)
    - meta.json: Metadata with satisfiable status and PM result

    Args:
        scenario: Scenario being processed
        output_dir: Scenario directory (contains assets/)
        lock_result: Result of lock operation

    Returns:
        Path to generated SBOM file, or None if generation failed
    """
    sbom_path = output_dir / "expected.cdx.json"
    meta_path = output_dir / "meta.json"

    try:
        # Always generate meta.json with PM result
        satisfiable = lock_result.status == LockStatus.SUCCESS
        generate_meta_file(
            output_path=meta_path,
            satisfiable=satisfiable,
            exit_code=lock_result.exit_code or 0,
            stdout=lock_result.stdout or "",
            stderr=lock_result.stderr or "",
        )

        # Only generate SBOM if lock succeeded
        if lock_result.status == LockStatus.SUCCESS:
            lock_file = output_dir / "assets" / "uv.lock"
            if lock_file.exists():
                packages = _parse_uv_lock(lock_file)
                return generate_sbom_file(
                    scenario_name=scenario.name,
                    output_path=sbom_path,
                    packages=packages,
                )

        return meta_path  # Return meta_path if no SBOM generated

    except Exception as e:
        logger.warning(f"Failed to generate SBOM/meta files: {e}")
        return None


@hookimpl
def get_output_dir(pm_name: str, base_dir: Path, scenario_name: str) -> Optional[Path]:
    """Get output directory for a UV scenario.

    Args:
        pm_name: Package manager name
        base_dir: Base output directory
        scenario_name: Name of the scenario

    Returns:
        Path to scenario output directory, or None if not UV.
    """
    if pm_name != "uv":
        return None
    return base_dir / "scenarios" / "uv" / scenario_name


@hookimpl
def validate_scenario(pm_name: str, scenario: Scenario) -> Optional[bool]:
    """Check if scenario is compatible with UV.

    Args:
        pm_name: Package manager name
        scenario: Scenario to validate

    Returns:
        True if compatible, False if not, None if not UV.
    """
    if pm_name != "uv":
        return None
    return scenario.source in ["packse"]


@hookimpl
def generate_sbom_for_lock(
    pm_name: str,
    scenario: Scenario,
    output_dir: Path,
    lock_result: LockResult
) -> Optional[Path]:
    """Generate SBOM and meta files for a UV lock result.

    Args:
        pm_name: Package manager name
        scenario: Scenario being processed
        output_dir: Scenario directory (contains assets/)
        lock_result: Result of lock operation

    Returns:
        Path to generated SBOM/meta file, or None if not UV.
    """
    if pm_name != "uv":
        return None
    return _generate_sbom_for_lock_impl(scenario, output_dir, lock_result)


