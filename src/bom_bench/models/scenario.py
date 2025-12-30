"""Scenario data models."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Requirement:
    """Represents a package requirement."""

    requirement: str
    """Full requirement string (e.g., 'package-a>=1.0.0')"""

    extras: list[str] = field(default_factory=list)
    """Optional extras for the requirement"""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Requirement":
        """Create Requirement from dictionary."""
        return cls(requirement=data.get("requirement", ""), extras=data.get("extras", []))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"requirement": self.requirement, "extras": self.extras}


@dataclass
class Root:
    """Root package configuration."""

    requires: list[Requirement] = field(default_factory=list)
    """List of package requirements"""

    requires_python: str | None = None
    """Python version requirement (e.g., '>=3.12')"""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Root":
        """Create Root from dictionary."""
        requires = [Requirement.from_dict(r) for r in data.get("requires", [])]
        return cls(requires=requires, requires_python=data.get("requires_python"))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requires": [r.to_dict() for r in self.requires],
            "requires_python": self.requires_python,
        }


@dataclass
class ResolverOptions:
    """Resolver configuration options."""

    universal: bool = False
    """Whether this scenario uses universal resolution"""

    required_environments: list[str] = field(default_factory=list)
    """Required environments for universal resolution"""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResolverOptions":
        """Create ResolverOptions from dictionary."""
        return cls(
            universal=data.get("universal", False),
            required_environments=data.get("required_environments", []),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "universal": self.universal,
            "required_environments": self.required_environments,
        }


@dataclass
class ExpectedPackage:
    """Expected package from scenario resolution."""

    name: str
    """Package name"""

    version: str
    """Package version"""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExpectedPackage":
        """Create ExpectedPackage from dictionary."""
        return cls(name=data.get("name", ""), version=data.get("version", ""))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"name": self.name, "version": self.version}


@dataclass
class Expected:
    """Expected resolution results."""

    packages: list[ExpectedPackage] = field(default_factory=list)
    """List of expected packages in the resolution"""

    satisfiable: bool = True
    """Whether the scenario is expected to be satisfiable"""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Expected":
        """Create Expected from dictionary."""
        packages = [ExpectedPackage.from_dict(p) for p in data.get("packages", [])]
        return cls(packages=packages, satisfiable=data.get("satisfiable", True))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "packages": [p.to_dict() for p in self.packages],
            "satisfiable": self.satisfiable,
        }


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

    description: str | None = None
    """Human-readable description of the scenario"""

    expected: Expected | None = None
    """Expected resolution result (for benchmarking)"""

    source: str = "packse"
    """Data source that provided this scenario"""

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str = "packse") -> "Scenario":
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
            source=source,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for plugin injection."""
        result: dict[str, Any] = {
            "name": self.name,
            "root": self.root.to_dict(),
            "resolver_options": self.resolver_options.to_dict(),
            "description": self.description,
            "source": self.source,
        }
        if self.expected is not None:
            result["expected"] = self.expected.to_dict()
        return result


@dataclass
class ScenarioFilter:
    """Configuration for filtering scenarios."""

    universal_only: bool = True
    """Only include scenarios with universal=true"""

    exclude_patterns: list[str] = field(default_factory=lambda: ["example"])
    """Exclude scenarios whose names contain these patterns"""

    include_sources: list[str] | None = None
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
        return not (
            self.include_sources is not None and scenario.source not in self.include_sources
        )
