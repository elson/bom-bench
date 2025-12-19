"""Packse data source implementation."""

import sys
from pathlib import Path
from typing import List

import packse.fetch
import packse.inspect

from bom_bench.data.base import DataSource
from bom_bench.models.scenario import Scenario


class PackseDataSource(DataSource):
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
        super().__init__(data_dir)

    def fetch(self) -> None:
        """Fetch packse scenarios from repository.

        Uses packse.fetch.fetch() to download scenarios to data_dir.

        Raises:
            Exception: If fetching fails
        """
        if not self.data_dir.parent.exists():
            self.data_dir.parent.mkdir(parents=True, exist_ok=True)

        print(f"Fetching packse scenarios to {self.data_dir}...")
        try:
            packse.fetch.fetch(dest=self.data_dir)
            print(f"Successfully fetched packse scenarios ✓\n")
        except Exception as e:
            print(f"Error: Failed to fetch packse scenarios: {e}", file=sys.stderr)
            raise

    def load_scenarios(self) -> List[Scenario]:
        """Load packse scenarios from local directory.

        Uses packse.inspect API to discover and parse scenario files,
        converting them to normalized Scenario objects.

        Returns:
            List of Scenario objects

        Raises:
            Exception: If loading fails
        """
        if not self.data_dir.exists():
            print(f"Warning: Packse directory {self.data_dir} not found", file=sys.stderr)
            return []

        try:
            # Find all scenario files
            scenario_files = list(packse.inspect.find_scenario_files(self.data_dir))

            if not scenario_files:
                print(f"Warning: No packse scenario files found in {self.data_dir}", file=sys.stderr)
                return []

            # Load scenarios using packse API
            # no_hash=True gives us full package names without hash suffixes
            template_vars = packse.inspect.variables_for_templates(
                scenario_files,
                no_hash=True
            )

            scenario_dicts = template_vars.get("scenarios", [])

            if not scenario_dicts:
                print(f"Warning: No scenarios loaded from packse", file=sys.stderr)
                return []

            # Convert to normalized Scenario objects
            scenarios = [
                Scenario.from_dict(scenario_dict, source=self.name)
                for scenario_dict in scenario_dicts
            ]

            print(f"Loaded {len(scenarios)} packse scenarios")
            return scenarios

        except Exception as e:
            print(f"Error: Failed to load packse scenarios: {e}", file=sys.stderr)
            raise

    def needs_fetch(self) -> bool:
        """Check if packse scenarios need to be fetched.

        Returns:
            True if data_dir doesn't exist, False otherwise
        """
        return not self.data_dir.exists()
