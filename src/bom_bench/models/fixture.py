from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bom_bench.sandbox.mise import ToolSpec


@dataclass
class FixtureSetEnvironment:
    """Mise configuration for a fixture set - shared by all fixtures in the set."""

    tools: list[ToolSpec]
    env_vars: dict[str, str]
    registry_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> FixtureSetEnvironment:
        """Create a FixtureSetEnvironment from a dictionary."""
        from bom_bench.sandbox.mise import ToolSpec

        tools = [ToolSpec(name=t["name"], version=t["version"]) for t in data.get("tools", [])]
        return cls(
            tools=tools,
            env_vars=data.get("env_vars", {}),
            registry_url=data.get("registry_url"),
        )


@dataclass
class FixtureFiles:
    """Files that comprise a fixture's test project."""

    manifest: Path
    lock_file: Path | None
    expected_sbom: Path | None
    meta: Path

    @classmethod
    def from_dict(cls, data: dict) -> FixtureFiles:
        """Create FixtureFiles from a dictionary."""
        return cls(
            manifest=Path(data["manifest"]),
            lock_file=Path(data["lock_file"]) if data.get("lock_file") else None,
            expected_sbom=Path(data["expected_sbom"]) if data.get("expected_sbom") else None,
            meta=Path(data["meta"]),
        )


@dataclass
class Fixture:
    """A single test case within a FixtureSet.

    Inherits environment from its parent FixtureSet.
    """

    name: str
    files: FixtureFiles
    satisfiable: bool
    description: str | None = None

    @property
    def project_dir(self) -> Path:
        """Directory containing the project files."""
        return self.files.manifest.parent

    @classmethod
    def from_dict(cls, data: dict) -> Fixture:
        """Create a Fixture from a dictionary."""
        return cls(
            name=data["name"],
            files=FixtureFiles.from_dict(data["files"]),
            satisfiable=data["satisfiable"],
            description=data.get("description"),
        )


@dataclass
class FixtureSet:
    """A collection of related fixtures provided by a plugin.

    All fixtures in a set share the same environment configuration.
    Example: "packse" fixture set with uv 0.5.11, python 3.12, packse registry.
    """

    name: str
    description: str
    ecosystem: str
    environment: FixtureSetEnvironment
    fixtures: list[Fixture] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> FixtureSet:
        """Create a FixtureSet from a dictionary."""
        environment = FixtureSetEnvironment.from_dict(data["environment"])
        fixtures = [Fixture.from_dict(f) for f in data.get("fixtures", [])]

        return cls(
            name=data["name"],
            description=data["description"],
            ecosystem=data["ecosystem"],
            environment=environment,
            fixtures=fixtures,
        )
