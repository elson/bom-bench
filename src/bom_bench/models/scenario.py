"""Scenario data models."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Requirement:
    """Represents a package requirement."""

    requirement: str
    """Full requirement string (e.g., 'package-a>=1.0.0')"""

    extras: List[str] = field(default_factory=list)
    """Optional extras for the requirement"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Requirement":
        """Create Requirement from dictionary.

        Args:
            data: Dictionary with 'requirement' and optional 'extras' keys

        Returns:
            Requirement instance
        """
        return cls(
            requirement=data.get("requirement", ""),
            extras=data.get("extras", [])
        )


@dataclass
class Root:
    """Root package configuration."""

    requires: List[Requirement] = field(default_factory=list)
    """List of package requirements"""

    requires_python: Optional[str] = None
    """Python version requirement (e.g., '>=3.12')"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Root":
        """Create Root from dictionary.

        Args:
            data: Dictionary with 'requires' and optional 'requires_python' keys

        Returns:
            Root instance
        """
        requires = [
            Requirement.from_dict(r)
            for r in data.get("requires", [])
        ]

        return cls(
            requires=requires,
            requires_python=data.get("requires_python")
        )


@dataclass
class ResolverOptions:
    """Resolver configuration options."""

    universal: bool = False
    """Whether this scenario uses universal resolution"""

    required_environments: List[str] = field(default_factory=list)
    """Required environments for universal resolution"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResolverOptions":
        """Create ResolverOptions from dictionary.

        Args:
            data: Dictionary with resolver option keys

        Returns:
            ResolverOptions instance
        """
        return cls(
            universal=data.get("universal", False),
            required_environments=data.get("required_environments", [])
        )


@dataclass
class ExpectedPackage:
    """Expected package from scenario resolution."""

    name: str
    """Package name"""

    version: str
    """Package version"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExpectedPackage":
        """Create ExpectedPackage from dictionary.

        Args:
            data: Dictionary with 'name' and 'version' keys

        Returns:
            ExpectedPackage instance
        """
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "")
        )


@dataclass
class Expected:
    """Expected resolution results."""

    packages: List[ExpectedPackage] = field(default_factory=list)
    """List of expected packages in the resolution"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Expected":
        """Create Expected from dictionary.

        Args:
            data: Dictionary with 'packages' key

        Returns:
            Expected instance
        """
        packages = [
            ExpectedPackage.from_dict(p)
            for p in data.get("packages", [])
        ]

        return cls(packages=packages)


@dataclass
class Scenario:
    """Represents a packse scenario (or other data source scenario).

    This is the normalized format that all data sources must produce.
    """

    name: str
    """Unique scenario identifier"""

    root: Root
    """Root package configuration"""

    resolver_options: ResolverOptions
    """Resolver-specific options"""

    description: Optional[str] = None
    """Human-readable description of the scenario"""

    expected: Optional[Expected] = None
    """Expected resolution result (for benchmarking)"""

    source: str = "packse"
    """Data source that provided this scenario"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any], source: str = "packse") -> "Scenario":
        """Create Scenario from packse dictionary.

        Args:
            data: Scenario dictionary from packse or other data source
            source: Name of the data source (default: "packse")

        Returns:
            Scenario instance
        """
        root_data = data.get("root", {})
        root = Root.from_dict(root_data)

        resolver_data = data.get("resolver_options", {})
        resolver_options = ResolverOptions.from_dict(resolver_data)

        expected_data = data.get("expected")
        expected = Expected.from_dict(expected_data) if expected_data else None

        return cls(
            name=data.get("name", ""),
            root=root,
            resolver_options=resolver_options,
            description=data.get("description"),
            expected=expected,
            source=source
        )


@dataclass
class ScenarioFilter:
    """Configuration for filtering scenarios."""

    universal_only: bool = True
    """Only include scenarios with universal=true"""

    exclude_patterns: List[str] = field(default_factory=lambda: ["example"])
    """Exclude scenarios whose names contain these patterns"""

    include_sources: Optional[List[str]] = None
    """Only include scenarios from these sources (None = all sources)"""

    def matches(self, scenario: Scenario) -> bool:
        """Check if a scenario matches the filter criteria.

        Args:
            scenario: Scenario to check

        Returns:
            True if scenario matches filter, False otherwise
        """
        # Check universal requirement
        if self.universal_only and not scenario.resolver_options.universal:
            return False

        # Check exclude patterns
        name_lower = scenario.name.lower()
        if any(pattern.lower() in name_lower for pattern in self.exclude_patterns):
            return False

        # Check source filter
        if self.include_sources is not None:
            if scenario.source not in self.include_sources:
                return False

        return True
