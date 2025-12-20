"""Gradle build tool implementation (STUB - Not yet implemented).

This is a stub implementation showing how to add Gradle as a package manager.
Gradle is a build automation tool used primarily for Java/Kotlin projects.

Implementation TODO:
- Generate build.gradle or build.gradle.kts files
- Translate scenarios to Gradle dependency DSL
- Run gradle dependencies --write-locks
- Handle configuration-specific lock files
"""

from pathlib import Path
from bom_bench.models.scenario import Scenario
from bom_bench.models.result import LockResult, LockStatus
from bom_bench.package_managers.base import PackageManager


class GradlePackageManager(PackageManager):
    """Gradle build tool implementation (STUB).

    Gradle is a versatile build automation tool that:
    - Uses Groovy or Kotlin DSL for build configuration
    - Supports dependency locking for reproducible builds
    - Handles complex multi-project builds

    Output structure:
    - output/gradle/{scenario}/
        - build.gradle (Groovy DSL) or build.gradle.kts (Kotlin DSL)
        - gradle/dependency-locks/ (lock files per configuration)
        - gradle-output.txt (command output log)

    Data source compatibility:
    - Supports: gradle-testkit (Gradle dependency test scenarios)
    - Future: Maven repository fixtures, custom Java scenarios

    Translation notes:
    - Python packages → Maven coordinates (group:artifact:version)
    - Version constraints: Different syntax for Gradle
    - Configurations: compile, runtime, testCompile, etc.
    """

    name = "gradle"
    ecosystem = "java"

    def generate_manifest(
        self,
        scenario: Scenario,
        output_dir: Path
    ) -> Path:
        """Generate build.gradle for Gradle.

        Args:
            scenario: Scenario to generate manifest for
            output_dir: Directory where manifest file should be written

        Returns:
            Path to the generated build.gradle file

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "Gradle package manager is not yet implemented. "
            "See src/bom_bench/package_managers/gradle.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Use src/bom_bench/generators/xml.py or create gradle_dsl.py
        # 2. Translate scenario.root.requires to Gradle dependencies
        # 3. Generate build.gradle with dependency block
        # 4. Add dependency locking configuration
        # 5. Return path to build.gradle

    def run_lock(
        self,
        project_dir: Path,
        scenario_name: str,
        timeout: int = 120
    ) -> LockResult:
        """Execute gradle dependencies --write-locks and capture output.

        Args:
            project_dir: Directory containing build.gradle
            scenario_name: Name of the scenario (for logging)
            timeout: Command timeout in seconds

        Returns:
            LockResult with execution details

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "Gradle package manager is not yet implemented. "
            "See src/bom_bench/package_managers/gradle.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Run: gradle dependencies --write-locks
        # 2. Capture stdout/stderr to gradle-output.txt
        # 3. Check if gradle/dependency-locks/*.lockfile was generated
        # 4. Return LockResult with status and file paths

    def validate_scenario(self, scenario: Scenario) -> bool:
        """Check if scenario is compatible with Gradle.

        Args:
            scenario: Scenario to validate

        Returns:
            True if scenario is compatible
        """
        # Gradle requires scenarios from gradle-testkit data source
        return scenario.source in ["gradle-testkit"]
