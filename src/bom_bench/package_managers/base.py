"""Base class for package managers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from bom_bench.models.scenario import Scenario
from bom_bench.models.result import LockResult


class PackageManager(ABC):
    """Abstract base class for package managers.

    Package managers are responsible for generating manifest files
    (pyproject.toml, package.json, build.gradle, etc.) and running
    lock/install commands to produce lock files.
    """

    name: str
    """Package manager name (e.g., 'uv', 'pip', 'pnpm', 'gradle')"""

    ecosystem: str
    """Ecosystem this package manager belongs to (e.g., 'python', 'javascript', 'java')"""

    @abstractmethod
    def generate_manifest(
        self,
        scenario: Scenario,
        output_dir: Path
    ) -> Path:
        """Generate package manager-specific manifest file.

        Args:
            scenario: Scenario to generate manifest for
            output_dir: Directory where manifest file should be written

        Returns:
            Path to the generated manifest file

        Raises:
            Exception: If manifest generation fails
        """
        pass

    @abstractmethod
    def run_lock(
        self,
        project_dir: Path,
        scenario_name: str,
        timeout: int = 120
    ) -> LockResult:
        """Execute lock/install command and capture output.

        Args:
            project_dir: Directory containing the manifest file
            scenario_name: Name of the scenario (for logging)
            timeout: Command timeout in seconds (default: 120)

        Returns:
            LockResult with execution details

        Raises:
            Exception: If lock command execution fails critically
        """
        pass

    @abstractmethod
    def validate_scenario(self, scenario: Scenario) -> bool:
        """Check if scenario is compatible with this package manager.

        Args:
            scenario: Scenario to validate

        Returns:
            True if scenario is compatible, False otherwise
        """
        pass

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

    def supports_source(self, source_name: str) -> bool:
        """Check if this package manager supports a given data source.

        Args:
            source_name: Name of the data source

        Returns:
            True if supported, False otherwise
        """
        from bom_bench.config import DATA_SOURCE_PM_MAPPING

        supported_pms = DATA_SOURCE_PM_MAPPING.get(source_name, [])
        return self.name in supported_pms
