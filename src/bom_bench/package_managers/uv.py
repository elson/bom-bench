"""UV package manager plugin.

This plugin provides support for the UV Python package manager,
including loading packse scenarios, generating pyproject.toml manifests,
and running uv lock commands.
"""

import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional

import pluggy

import packse.fetch
import packse.inspect

from bom_bench.config import (
    PACKSE_INDEX_URL,
    LOCK_TIMEOUT_SECONDS,
    PROJECT_NAME,
    PROJECT_VERSION,
    DEFAULT_PACKSE_DIR,
)
from bom_bench.generators.sbom.cyclonedx import generate_sbom_result
from bom_bench.generators.uv import generate_pyproject_toml
from bom_bench.logging_config import get_logger
from bom_bench.models.package_manager import PMInfo
from bom_bench.models.result import LockResult, LockStatus
from bom_bench.models.scenario import Scenario
from bom_bench.parsers.uv_lock import parse_uv_lock

logger = get_logger(__name__)

hookimpl = pluggy.HookimplMarker("bom_bench")


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
def register_package_managers() -> List[PMInfo]:
    """Register UV package manager."""
    return [
        PMInfo(
            name="uv",
            ecosystem="python",
            description="Fast Python package manager and resolver",
            data_source="packse",
            version=_get_uv_version()
        )
    ]


@hookimpl
def check_pm_available(pm_name: str) -> Optional[bool]:
    """Check if UV is available."""
    if pm_name != "uv":
        return None
    return shutil.which("uv") is not None


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
        output_dir: Output directory

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
    content = generate_pyproject_toml(
        name=PROJECT_NAME,
        version=PROJECT_VERSION,
        dependencies=dependencies,
        requires_python=requires_python,
        required_environments=required_environments if required_environments else None
    )

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write pyproject.toml file
    manifest_path = output_dir / "pyproject.toml"
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
        project_dir: Directory containing the pyproject.toml
        scenario_name: Name of the scenario (for logging)
        timeout: Command timeout in seconds

    Returns:
        LockResult with execution details, or None if not handled.
    """
    if pm_name != "uv":
        return None

    output_file = project_dir / "uv-lock-output.txt"
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

        # Write output to file
        with open(output_file, "w") as f:
            f.write(f"Exit code: {result.returncode}\n\n")
            f.write("=== STDOUT ===\n")
            f.write(result.stdout)
            f.write("\n\n=== STDERR ===\n")
            f.write(result.stderr)

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
            output_file=output_file,
            lock_file=lock_file if lock_file.exists() else None,
            duration_seconds=duration
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time

        with open(output_file, "w") as f:
            f.write("Exit code: TIMEOUT\n\n")
            f.write(f"Error: Command timed out after {timeout} seconds\n")

        logger.warning(f"  Timeout: {scenario_name}")

        return LockResult(
            scenario_name=scenario_name,
            package_manager="uv",
            status=LockStatus.TIMEOUT,
            output_file=output_file,
            error_message=f"Command timed out after {timeout} seconds",
            duration_seconds=duration
        )

    except Exception as e:
        duration = time.time() - start_time

        with open(output_file, "w") as f:
            f.write(f"Exit code: ERROR\n\n")
            f.write(f"Error: {str(e)}\n")

        logger.error(f"  Error running uv lock for {scenario_name}: {e}")

        return LockResult(
            scenario_name=scenario_name,
            package_manager="uv",
            status=LockStatus.ERROR,
            output_file=output_file,
            error_message=str(e),
            duration_seconds=duration
        )


def generate_sbom_for_lock(
    scenario: Scenario,
    output_dir: Path,
    lock_result: LockResult
) -> Optional[Path]:
    """Generate SBOM result file with satisfiable status.

    This is a helper function called by the orchestration layer,
    not a hook.

    Always generates an expected.cdx.json file containing:
    - satisfiable: True if lock succeeded, False otherwise
    - sbom: CycloneDX SBOM (only if lock succeeded)

    Args:
        scenario: Scenario being processed
        output_dir: Directory to write SBOM
        lock_result: Result of lock operation

    Returns:
        Path to generated file, or None if generation failed
    """
    sbom_path = output_dir / "expected.cdx.json"

    try:
        if lock_result.status == LockStatus.SUCCESS:
            lock_file = output_dir / "uv.lock"
            if lock_file.exists():
                packages = parse_uv_lock(lock_file)
                return generate_sbom_result(
                    scenario_name=scenario.name,
                    output_path=sbom_path,
                    packages=packages,
                    satisfiable=True
                )
        else:
            return generate_sbom_result(
                scenario_name=scenario.name,
                output_path=sbom_path,
                packages=None,
                satisfiable=False
            )

    except Exception as e:
        logger.warning(f"Failed to generate SBOM result: {e}")
        return None


# Keep the class for backward compatibility during migration
class UVPackageManager:
    """UV package manager (deprecated - use plugin hooks instead)."""

    name = "uv"
    ecosystem = "python"

    def get_output_dir(self, base_dir: Path, scenario_name: str) -> Path:
        """Get output directory for a scenario.

        Creates hierarchical structure: base_dir/{package_manager}/{scenario_name}/

        Args:
            base_dir: Base output directory
            scenario_name: Name of the scenario

        Returns:
            Path to scenario-specific output directory
        """
        return base_dir / self.name / scenario_name

    def generate_manifest(self, scenario: Scenario, output_dir: Path) -> Path:
        """Generate pyproject.toml for UV."""
        path = generate_manifest("uv", scenario, output_dir)
        if path is None:
            raise RuntimeError("Failed to generate manifest")

        # Also run lock (old behavior)
        lock_result = run_lock("uv", output_dir, scenario.name)
        if lock_result:
            generate_sbom_for_lock(scenario, output_dir, lock_result)

        return path

    def run_lock(
        self,
        project_dir: Path,
        scenario_name: str,
        timeout: int = LOCK_TIMEOUT_SECONDS
    ) -> LockResult:
        """Execute uv lock command."""
        result = run_lock("uv", project_dir, scenario_name, timeout)
        if result is None:
            raise RuntimeError("Failed to run lock")
        return result

    def validate_scenario(self, scenario: Scenario) -> bool:
        """Check if scenario is compatible with UV."""
        return scenario.source in ["packse"]

    def supports_source(self, source_name: str) -> bool:
        """Check if UV supports a given data source."""
        return source_name == "packse"

    def generate_sbom_result_file(
        self,
        scenario: Scenario,
        output_dir: Path,
        lock_result: LockResult
    ) -> Optional[Path]:
        """Generate SBOM result file (backward compatibility wrapper)."""
        return generate_sbom_for_lock(scenario, output_dir, lock_result)
