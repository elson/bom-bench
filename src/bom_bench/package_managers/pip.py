"""Pip package manager implementation (STUB - Not yet implemented).

This is a stub implementation showing how to add pip as a package manager.
Pip uses requirements.txt or pyproject.toml + pip-compile for dependency management.

Implementation TODO:
- Generate pyproject.toml + requirements.in files
- Run pip-compile to generate requirements.txt
- Support different pip-compile options
- Handle environment markers and extras
"""

from pathlib import Path
from bom_bench.models.scenario import Scenario
from bom_bench.models.result import LockResult, LockStatus
from bom_bench.package_managers.base import PackageManager


class PipPackageManager(PackageManager):
    """Pip package manager implementation (STUB).

    Pip is a widely-used Python package manager that can work with:
    - requirements.txt (simple dependency list)
    - pyproject.toml + pip-compile (for reproducible builds)

    Output structure:
    - output/pip/{scenario}/
        - pyproject.toml (project metadata)
        - requirements.in (input dependencies)
        - requirements.txt (locked dependencies via pip-compile)
        - pip-compile-output.txt (command output log)

    Data source compatibility:
    - Supports: packse (Python packaging scenarios)
    - Future: Any Python package data source
    """

    name = "pip"
    ecosystem = "python"

    def generate_manifest(
        self,
        scenario: Scenario,
        output_dir: Path
    ) -> Path:
        """Generate pyproject.toml + requirements.in for pip.

        Args:
            scenario: Scenario to generate manifest for
            output_dir: Directory where manifest files should be written

        Returns:
            Path to the generated pyproject.toml file

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "Pip package manager is not yet implemented. "
            "See src/bom_bench/package_managers/pip.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Generate pyproject.toml (similar to UV)
        # 2. Generate requirements.in from scenario.root.requires
        # 3. Return path to pyproject.toml

    def run_lock(
        self,
        project_dir: Path,
        scenario_name: str,
        timeout: int = 120
    ) -> LockResult:
        """Execute pip-compile and capture output.

        Args:
            project_dir: Directory containing requirements.in
            scenario_name: Name of the scenario (for logging)
            timeout: Command timeout in seconds

        Returns:
            LockResult with execution details

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "Pip package manager is not yet implemented. "
            "See src/bom_bench/package_managers/pip.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Run: pip-compile requirements.in --index-url {PACKSE_INDEX_URL}
        # 2. Capture stdout/stderr to pip-compile-output.txt
        # 3. Check if requirements.txt was generated
        # 4. Return LockResult with status and file paths

    def validate_scenario(self, scenario: Scenario) -> bool:
        """Check if scenario is compatible with pip.

        Args:
            scenario: Scenario to validate

        Returns:
            True if scenario is compatible
        """
        # Pip supports the same scenarios as UV (packse)
        return scenario.source in ["packse"]
