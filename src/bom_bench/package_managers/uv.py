"""UV package manager plugin.

This plugin provides support for the UV Python package manager,
including loading packse scenarios, generating pyproject.toml manifests,
and running uv lock commands.
"""

import shutil
import subprocess
import time
from pathlib import Path

import tomlkit

from bom_bench import hookimpl
from bom_bench.generators.sbom.cyclonedx import generate_meta_file, generate_sbom_file
from bom_bench.logging_config import get_logger
from bom_bench.models.result import LockResult, LockStatus
from bom_bench.models.scenario import ExpectedPackage, Scenario

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
    dependencies: list[str],
    requires_python: str | None = None,
    required_environments: list[str] | None = None,
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
    doc = tomlkit.document()

    # [project] section
    project = tomlkit.table()
    project["name"] = name
    project["version"] = version
    project["dependencies"] = dependencies if dependencies else []

    if requires_python:
        project["requires-python"] = requires_python

    doc["project"] = project

    # [tool.uv] section for required environments
    if required_environments:
        if "tool" not in doc:
            doc["tool"] = tomlkit.table()

        uv_table = tomlkit.table()
        uv_table["required-environments"] = required_environments
        doc["tool"]["uv"] = uv_table

    return tomlkit.dumps(doc)


def _parse_uv_lock(lock_file_path: Path) -> list[ExpectedPackage]:
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
        with open(lock_file_path, encoding="utf-8") as f:
            lock_data = tomlkit.load(f)

        packages = []
        for package in lock_data.get("package", []):
            # Skip the virtual project package
            source = package.get("source", {})
            if source.get("virtual") == ".":
                continue

            name = package.get("name")
            version = package.get("version")

            if name and version:
                packages.append(ExpectedPackage(name=name, version=version))

        return packages

    except Exception as e:
        raise Exception(f"Failed to parse uv.lock file: {e}") from e


def _get_uv_version() -> str | None:
    """Get UV version if installed."""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=10)
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
        "supported_sources": ["packse"],
        "installed": shutil.which("uv") is not None,
        "version": _get_uv_version(),
    }


def _generate_sbom_for_lock_impl(
    scenario: Scenario, output_dir: Path, lock_result: LockResult
) -> Path | None:
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
def process_scenario(
    pm_name: str, scenario: Scenario, output_dir: Path, timeout: int = LOCK_TIMEOUT_SECONDS
) -> dict | None:
    """Process a scenario: generate manifest, lock, and SBOM.

    This is the new simplified hook that combines generate_manifest, run_lock,
    and generate_sbom_for_lock into a single atomic operation.

    Args:
        pm_name: Package manager name
        scenario: Scenario to process
        output_dir: Scenario output directory
        timeout: Timeout in seconds

    Returns:
        Dict with result info, or None if not UV.
    """
    if pm_name != "uv":
        return None

    start_time = time.time()

    try:
        # 1. Generate manifest (pyproject.toml)
        # Extract dependencies from scenario
        dependencies = [req.requirement for req in scenario.root.requires]
        requires_python = scenario.root.requires_python
        required_environments = scenario.resolver_options.required_environments

        # Generate pyproject.toml content
        content = _generate_pyproject_toml(
            name=PROJECT_NAME,
            version=PROJECT_VERSION,
            dependencies=dependencies,
            requires_python=requires_python,
            required_environments=required_environments if required_environments else None,
        )

        # Write to assets subdirectory
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = assets_dir / "pyproject.toml"
        manifest_path.write_text(content)

        # 2. Run lock command
        lock_file = assets_dir / "uv.lock"
        lock_start_time = time.time()

        try:
            # Run uv lock with the packse index URL
            result = subprocess.run(
                ["uv", "lock", "--index-url", PACKSE_INDEX_URL],
                cwd=assets_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            lock_duration = time.time() - lock_start_time

            # Determine lock status
            lock_status = LockStatus.SUCCESS if result.returncode == 0 else LockStatus.FAILED

            lock_result = LockResult(
                scenario_name=scenario.name,
                package_manager="uv",
                status=lock_status,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                lock_file=lock_file if lock_file.exists() else None,
                duration_seconds=lock_duration,
            )

        except subprocess.TimeoutExpired:
            lock_duration = time.time() - lock_start_time
            logger.warning(f"  Timeout: {scenario.name}")

            lock_result = LockResult(
                scenario_name=scenario.name,
                package_manager="uv",
                status=LockStatus.TIMEOUT,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                error_message=f"Command timed out after {timeout} seconds",
                duration_seconds=lock_duration,
            )

        # 3. Generate SBOM and meta files
        _generate_sbom_for_lock_impl(scenario, output_dir, lock_result)

        duration = time.time() - start_time

        # Determine status
        if lock_result.status == LockStatus.SUCCESS:
            status = "success"
        elif lock_result.status == LockStatus.TIMEOUT:
            status = "timeout"
        else:
            # Check if it's unsatisfiable (meta.json exists but no SBOM)
            meta_path = output_dir / "meta.json"
            sbom_path = output_dir / "expected.cdx.json"
            status = "unsatisfiable" if meta_path.exists() and not sbom_path.exists() else "failed"

        # Build result dict
        result = {
            "pm_name": "uv",
            "status": status,
            "duration_seconds": duration,
            "exit_code": lock_result.exit_code or 0,
            "manifest_path": str(manifest_path),
            "lock_file_path": str(lock_result.lock_file) if lock_result.lock_file else None,
        }

        # Add optional paths if they exist
        sbom_path = output_dir / "expected.cdx.json"
        if sbom_path.exists():
            result["sbom_path"] = str(sbom_path)

        meta_path = output_dir / "meta.json"
        if meta_path.exists():
            result["meta_path"] = str(meta_path)

        if lock_result.error_message:
            result["error_message"] = lock_result.error_message

        return result

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error processing scenario {scenario.name}: {e}")
        return {
            "pm_name": "uv",
            "status": "failed",
            "duration_seconds": duration,
            "exit_code": 1,
            "error_message": str(e),
        }
