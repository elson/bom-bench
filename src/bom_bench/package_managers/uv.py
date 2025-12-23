"""UV package manager implementation."""

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from bom_bench.config import PACKSE_INDEX_URL, LOCK_TIMEOUT_SECONDS, PROJECT_NAME, PROJECT_VERSION
from bom_bench.generators.sbom.cyclonedx import generate_cyclonedx_sbom
from bom_bench.generators.uv import generate_pyproject_toml
from bom_bench.models.result import LockResult, LockStatus
from bom_bench.models.scenario import Scenario
from bom_bench.package_managers.base import PackageManager


class UVPackageManager(PackageManager):
    """UV package manager implementation for Python projects."""

    name = "uv"
    ecosystem = "python"

    def generate_manifest(
        self,
        scenario: Scenario,
        output_dir: Path
    ) -> Path:
        """Generate pyproject.toml for UV.

        Args:
            scenario: Scenario to generate manifest for
            output_dir: Directory where manifest file should be written

        Returns:
            Path to the generated pyproject.toml file

        Raises:
            Exception: If manifest generation fails
        """
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

        # Generate expected SBOM if expected data exists
        if scenario.expected and scenario.expected.packages:
            self.generate_expected_sbom(scenario, output_dir)

        return manifest_path

    def generate_expected_sbom(
        self,
        scenario: Scenario,
        output_dir: Path
    ) -> Optional[Path]:
        """Generate expected.cdx.json from scenario expected data.

        Creates a CycloneDX SBOM containing the expected packages from
        the scenario. This serves as groundtruth data for benchmarking.

        Args:
            scenario: Scenario with expected package data
            output_dir: Directory to write SBOM

        Returns:
            Path to generated SBOM, or None if no expected data
        """
        if not scenario.expected or not scenario.expected.packages:
            return None

        sbom_path = output_dir / "expected.cdx.json"

        return generate_cyclonedx_sbom(
            scenario_name=scenario.name,
            expected_packages=scenario.expected.packages,
            output_path=sbom_path
        )

    def run_lock(
        self,
        project_dir: Path,
        scenario_name: str,
        timeout: int = LOCK_TIMEOUT_SECONDS
    ) -> LockResult:
        """Execute uv lock command and capture output.

        Args:
            project_dir: Directory containing the pyproject.toml
            scenario_name: Name of the scenario (for logging)
            timeout: Command timeout in seconds

        Returns:
            LockResult with execution details
        """
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
                package_manager=self.name,
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

            print(f"  Timeout: {scenario_name}", file=sys.stderr)

            return LockResult(
                scenario_name=scenario_name,
                package_manager=self.name,
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

            print(f"  Error running uv lock for {scenario_name}: {e}", file=sys.stderr)

            return LockResult(
                scenario_name=scenario_name,
                package_manager=self.name,
                status=LockStatus.ERROR,
                output_file=output_file,
                error_message=str(e),
                duration_seconds=duration
            )

    def validate_scenario(self, scenario: Scenario) -> bool:
        """Check if scenario is compatible with UV.

        UV can handle any Python package scenario from packse.

        Args:
            scenario: Scenario to validate

        Returns:
            True if scenario is compatible (always True for UV with packse scenarios)
        """
        # UV supports scenarios from packse data source
        return scenario.source in ["packse"]
