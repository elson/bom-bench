"""Scenario loading and filtering across multiple data sources."""

from bom_bench.config import DEFAULT_DATA_SOURCE
from bom_bench.data import get_data_source, get_sources_for_pm
from bom_bench.logging_config import get_logger
from bom_bench.models.scenario import Scenario, ScenarioFilter

logger = get_logger(__name__)


class ScenarioLoader:
    """Loads and filters scenarios from one or more data sources."""

    def __init__(self, auto_fetch: bool = True):
        """Initialize ScenarioLoader.

        Args:
            auto_fetch: Whether to automatically fetch data sources if needed
        """
        self.auto_fetch = auto_fetch

    def load_from_source(
        self, source_name: str, filter_config: ScenarioFilter | None = None
    ) -> list[Scenario]:
        """Load scenarios from a single data source.

        Args:
            source_name: Name of the data source (e.g., 'packse')
            filter_config: Optional filter to apply to scenarios

        Returns:
            List of filtered scenarios
        """
        # Get data source instance
        source = get_data_source(source_name)

        # Fetch if needed
        if self.auto_fetch and source.needs_fetch():
            logger.info(f"Data source '{source_name}' needs fetching...")
            source.fetch()

        # Load scenarios
        scenarios = source.load_scenarios()

        # Apply filter if provided
        if filter_config:
            scenarios = [s for s in scenarios if filter_config.matches(s)]

        return scenarios

    def load_for_package_manager(
        self,
        package_manager: str,
        filter_config: ScenarioFilter | None = None,
        sources: list[str] | None = None,
    ) -> list[Scenario]:
        """Load scenarios compatible with a specific package manager.

        Args:
            package_manager: Package manager name (e.g., 'uv', 'pip')
            filter_config: Optional filter to apply
            sources: Optional list of source names to use (defaults to all compatible)

        Returns:
            List of scenarios from all compatible sources
        """
        # Determine which sources to use
        if sources is None:
            sources = get_sources_for_pm(package_manager)

        if not sources:
            logger.warning(f"No data sources support package manager '{package_manager}'")
            return []

        # Update filter to only include specified sources
        if filter_config is None:
            filter_config = ScenarioFilter()

        if filter_config.include_sources is None:
            filter_config.include_sources = sources
        else:
            # Intersect with requested sources
            filter_config.include_sources = [
                s for s in filter_config.include_sources if s in sources
            ]

        # Load from all sources
        all_scenarios = []
        for source_name in sources:
            scenarios = self.load_from_source(source_name, filter_config)
            all_scenarios.extend(scenarios)

        return all_scenarios

    def load_default(self, filter_config: ScenarioFilter | None = None) -> list[Scenario]:
        """Load scenarios from the default data source.

        Args:
            filter_config: Optional filter to apply

        Returns:
            List of scenarios from default source
        """
        return self.load_from_source(DEFAULT_DATA_SOURCE, filter_config)

    def load_all_sources(self, filter_config: ScenarioFilter | None = None) -> list[Scenario]:
        """Load scenarios from all available data sources.

        Args:
            filter_config: Optional filter to apply

        Returns:
            List of scenarios from all sources
        """
        from bom_bench.data import get_available_sources

        all_scenarios = []
        for source_name in get_available_sources():
            scenarios = self.load_from_source(source_name, filter_config)
            all_scenarios.extend(scenarios)

        return all_scenarios
