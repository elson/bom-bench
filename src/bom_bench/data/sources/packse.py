"""Packse data source implementation."""

from pathlib import Path

import packse.fetch
import packse.inspect

from bom_bench.logging_config import get_logger
from bom_bench.models.scenario import Scenario

logger = get_logger(__name__)


class PackseDataSource:
    """Data source for packse Python packaging scenarios.

    Packse provides test scenarios for Python dependency resolution,
    supporting both uv and pip package managers.
    """

    name = "packse"
    supported_pms = ["uv", "pip"]

    def __init__(self, data_dir: Path):
        """Initialize PackseDataSource.

        Args:
            data_dir: Directory where packse scenarios will be stored
        """
        self.data_dir = data_dir

    def fetch(self) -> None:
        """Fetch packse scenarios from repository.

        Uses packse.fetch.fetch() to download scenarios to data_dir.

        Raises:
            Exception: If fetching fails
        """
        if not self.data_dir.parent.exists():
            self.data_dir.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Fetching packse scenarios to {self.data_dir}...")
        try:
            packse.fetch.fetch(dest=self.data_dir)
            logger.info("Successfully fetched packse scenarios")
        except Exception as e:
            logger.error(f"Failed to fetch packse scenarios: {e}")
            raise

    def load_scenarios(self) -> list[Scenario]:
        """Load packse scenarios from local directory.

        Uses packse.inspect API to discover and parse scenario files,
        converting them to normalized Scenario objects.

        Returns:
            List of Scenario objects

        Raises:
            Exception: If loading fails
        """
        if not self.data_dir.exists():
            logger.warning(f"Packse directory {self.data_dir} not found")
            return []

        try:
            # Find all scenario files
            scenario_files = list(packse.inspect.find_scenario_files(self.data_dir))

            if not scenario_files:
                logger.warning(f"No packse scenario files found in {self.data_dir}")
                return []

            # Load scenarios using packse API
            # no_hash=True gives us full package names without hash suffixes
            template_vars = packse.inspect.variables_for_templates(scenario_files, no_hash=True)

            scenario_dicts = template_vars.get("scenarios", [])

            if not scenario_dicts:
                logger.warning("No scenarios loaded from packse")
                return []

            # Convert to normalized Scenario objects
            scenarios = [
                Scenario.from_dict(scenario_dict, source=self.name)
                for scenario_dict in scenario_dicts
            ]

            logger.info(f"Loaded {len(scenarios)} packse scenarios")
            return scenarios

        except Exception as e:
            logger.error(f"Failed to load packse scenarios: {e}")
            raise

    def needs_fetch(self) -> bool:
        """Check if packse scenarios need to be fetched.

        Returns:
            True if data_dir doesn't exist, False otherwise
        """
        return not self.data_dir.exists()
