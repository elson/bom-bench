"""Gradle TestKit data source (STUB - Not yet implemented).

This data source will fetch Gradle dependency resolution test scenarios
and normalize them into the standard Scenario format for use with Gradle.

Data Source:
- Repository: https://github.com/gradle/gradle
- Location: subprojects/dependency-management/src/integTest/
- Format: build.gradle files with specific dependency scenarios

Implementation TODO:
- Clone or download Gradle repository
- Parse integration test scenarios
- Normalize to Scenario format
- Map Maven coordinates to requirements
"""

from pathlib import Path
from typing import List
from bom_bench.data.base import DataSource
from bom_bench.models.scenario import Scenario


class GradleTestKitDataSource(DataSource):
    """Data source for Gradle TestKit scenarios (STUB).

    This data source fetches test scenarios from the Gradle repository,
    which contains comprehensive integration tests for dependency resolution,
    version conflicts, platform constraints, and other Gradle features.

    Attributes:
        name: Data source identifier ("gradle-testkit")
        supported_pms: Package managers that can use this source (["gradle"])
        data_dir: Local directory where Gradle test data is stored
    """

    name = "gradle-testkit"
    supported_pms = ["gradle"]

    def __init__(self, data_dir: Path):
        """Initialize gradle-testkit data source.

        Args:
            data_dir: Directory where Gradle test data will be stored
        """
        self.data_dir = data_dir

    def fetch(self) -> None:
        """Fetch Gradle test scenarios from repository.

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "gradle-testkit data source is not yet implemented. "
            "See src/bom_bench/data/sources/gradle_testkit.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Clone Gradle repository or download specific test directories
        #    git clone https://github.com/gradle/gradle {data_dir}/gradle
        # 2. Or use GitHub API to download integration test directories
        # 3. Focus on: subprojects/dependency-management/src/integTest/
        # 4. Create data_dir if it doesn't exist

    def load_scenarios(self) -> List[Scenario]:
        """Load and normalize Gradle test scenarios.

        Returns:
            List of Scenario objects

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "gradle-testkit data source is not yet implemented. "
            "See src/bom_bench/data/sources/gradle_testkit.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Find all build.gradle files in integration test directories
        # 2. Parse each build.gradle (Groovy DSL parsing)
        # 3. Extract dependencies from dependencies {} block
        # 4. Normalize to Scenario format:
        #    - name: test case name
        #    - root.requires: convert Maven coordinates to Requirement objects
        #    - resolver_options: extract Gradle-specific options
        #    - source: "gradle-testkit"
        # 5. Filter for relevant dependency resolution test cases
        # 6. Return list of Scenario objects

    def needs_fetch(self) -> bool:
        """Check if Gradle test data needs to be fetched.

        Returns:
            True if data directory doesn't exist or is empty
        """
        return not self.data_dir.exists() or not any(self.data_dir.iterdir())
