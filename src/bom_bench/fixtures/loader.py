"""Fixture set loader for bom-bench.

Loads fixture sets from plugins via the register_fixture_sets hook.
"""

from __future__ import annotations

import bom_bench
from bom_bench.models.fixture import FixtureSet
from bom_bench.plugins import pm as default_pm


class FixtureSetLoader:
    """Loads fixture sets from plugins.

    Fixture sets are discovered via the register_fixture_sets hook.
    Each plugin can return multiple fixture sets.

    Usage:
        loader = FixtureSetLoader()
        fixture_sets = loader.load_all()

        # Or load a specific fixture set by name
        packse_set = loader.load_by_name("packse")
    """

    def __init__(self, pm=None):
        """Initialize the loader.

        Args:
            pm: Plugin manager to use. Defaults to the global plugin manager.
        """
        self.pm = pm if pm is not None else default_pm

    def load_all(self) -> list[FixtureSet]:
        """Load all fixture sets from all plugins.

        Returns:
            List of FixtureSet objects from all registered plugins.
        """
        fixture_sets = []

        results = self.pm.hook.register_fixture_sets(bom_bench=bom_bench)

        for plugin_result in results:
            if plugin_result is None:
                continue

            for fixture_set_dict in plugin_result:
                fixture_set = FixtureSet.from_dict(fixture_set_dict)
                fixture_sets.append(fixture_set)

        return fixture_sets

    def load_by_name(self, name: str) -> FixtureSet | None:
        """Load a specific fixture set by name.

        Args:
            name: Name of the fixture set to load.

        Returns:
            The FixtureSet if found, None otherwise.
        """
        fixture_sets = self.load_all()

        for fixture_set in fixture_sets:
            if fixture_set.name == name:
                return fixture_set

        return None

    def load_by_ecosystem(self, ecosystem: str) -> list[FixtureSet]:
        """Load all fixture sets for a specific ecosystem.

        Args:
            ecosystem: Ecosystem to filter by (e.g., "python", "javascript").

        Returns:
            List of FixtureSet objects matching the ecosystem.
        """
        fixture_sets = self.load_all()
        return [fs for fs in fixture_sets if fs.ecosystem == ecosystem]

    def get_fixture_set_names(self) -> list[str]:
        """Get names of all available fixture sets.

        Returns:
            List of fixture set names.
        """
        fixture_sets = self.load_all()
        return [fs.name for fs in fixture_sets]
