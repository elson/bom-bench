"""Base class for data sources."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from bom_bench.models.scenario import Scenario


class DataSource(ABC):
    """Abstract base class for data sources.

    Data sources are responsible for fetching and loading test scenarios
    from various sources (packse, pnpm-tests, gradle-testkit, etc.).
    Each data source produces normalized Scenario objects.
    """

    name: str
    """Data source name (e.g., 'packse', 'pnpm-tests')"""

    supported_pms: List[str]
    """List of package managers this source supports"""

    def __init__(self, data_dir: Path):
        """Initialize the data source.

        Args:
            data_dir: Base directory for this data source's files
        """
        self.data_dir = data_dir

    @abstractmethod
    def fetch(self) -> None:
        """Download/clone data source to local directory.

        Raises:
            Exception: If fetching fails
        """
        pass

    @abstractmethod
    def load_scenarios(self) -> List[Scenario]:
        """Load scenarios from data source, normalized to common format.

        Returns:
            List of Scenario objects

        Raises:
            Exception: If loading fails
        """
        pass

    @abstractmethod
    def needs_fetch(self) -> bool:
        """Check if data needs to be fetched.

        Returns:
            True if data should be fetched, False if already present
        """
        pass

    def get_scenarios_for_pm(self, package_manager: str) -> List[Scenario]:
        """Get scenarios compatible with a specific package manager.

        Args:
            package_manager: Package manager name (e.g., 'uv', 'pip')

        Returns:
            List of scenarios compatible with the package manager
        """
        if package_manager not in self.supported_pms:
            return []

        all_scenarios = self.load_scenarios()
        return [s for s in all_scenarios if s.source == self.name]
