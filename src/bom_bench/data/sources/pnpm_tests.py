"""pnpm test cases data source (STUB - Not yet implemented).

This data source will fetch test cases from the pnpm repository and normalize
them into the standard Scenario format for use with the pnpm package manager.

Data Source:
- Repository: https://github.com/pnpm/pnpm
- Location: test/fixtures/ or similar
- Format: package.json files with specific dependency scenarios

Implementation TODO:
- Clone or download pnpm repository
- Parse test fixtures from test/fixtures/
- Normalize to Scenario format
- Map npm package names to requirements
"""

from pathlib import Path
from typing import List
from bom_bench.data.base import DataSource
from bom_bench.models.scenario import Scenario


class PnpmTestsDataSource(DataSource):
    """Data source for pnpm test cases (STUB).

    This data source fetches test scenarios from the pnpm repository,
    which contains comprehensive test cases for package resolution,
    hoisting, workspaces, and other pnpm features.

    Attributes:
        name: Data source identifier ("pnpm-tests")
        supported_pms: Package managers that can use this source (["pnpm"])
        data_dir: Local directory where pnpm repo is cloned/downloaded
    """

    name = "pnpm-tests"
    supported_pms = ["pnpm"]

    def __init__(self, data_dir: Path):
        """Initialize pnpm-tests data source.

        Args:
            data_dir: Directory where pnpm test data will be stored
        """
        self.data_dir = data_dir

    def fetch(self) -> None:
        """Fetch pnpm test cases from repository.

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "pnpm-tests data source is not yet implemented. "
            "See src/bom_bench/data/sources/pnpm_tests.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Clone pnpm repository or download tarball
        #    git clone https://github.com/pnpm/pnpm {data_dir}/pnpm
        # 2. Or use GitHub API to download specific test directories
        # 3. Create data_dir if it doesn't exist

    def load_scenarios(self) -> List[Scenario]:
        """Load and normalize pnpm test scenarios.

        Returns:
            List of Scenario objects

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "pnpm-tests data source is not yet implemented. "
            "See src/bom_bench/data/sources/pnpm_tests.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Find all package.json files in test/fixtures/
        # 2. Parse each package.json
        # 3. Extract dependencies, devDependencies
        # 4. Normalize to Scenario format:
        #    - name: fixture directory name
        #    - root.requires: convert dependencies to Requirement objects
        #    - resolver_options: extract pnpm-specific options
        #    - source: "pnpm-tests"
        # 5. Return list of Scenario objects

    def needs_fetch(self) -> bool:
        """Check if pnpm test data needs to be fetched.

        Returns:
            True if data directory doesn't exist or is empty
        """
        return not self.data_dir.exists() or not any(self.data_dir.iterdir())
