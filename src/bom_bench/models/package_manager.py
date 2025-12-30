"""Package manager metadata models."""

from dataclasses import dataclass
from enum import Enum


class ProcessStatus(Enum):
    """Status of scenario processing operation.

    Values:
        SUCCESS: Processing completed successfully
        FAILED: Processing failed due to error
        TIMEOUT: Processing exceeded timeout limit
        UNSATISFIABLE: Dependencies cannot be satisfied
    """

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNSATISFIABLE = "unsatisfiable"


@dataclass
class ProcessScenarioResult:
    """Result of processing a scenario with a package manager.

    This is the result returned by the process_scenario hook.
    Plugins write files to output_dir; framework discovers them by convention.

    Attributes:
        pm_name: Package manager name
        status: Processing status
        duration_seconds: Processing duration in seconds
        exit_code: Exit code from lock command
        error_message: Error message if failed
    """

    pm_name: str
    status: ProcessStatus
    duration_seconds: float
    exit_code: int
    error_message: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "ProcessScenarioResult":
        """Create ProcessScenarioResult from plugin dict.

        Args:
            d: Dict with result fields

        Returns:
            ProcessScenarioResult instance
        """
        return cls(
            pm_name=d["pm_name"],
            status=ProcessStatus(d["status"]),
            duration_seconds=d["duration_seconds"],
            exit_code=d["exit_code"],
            error_message=d.get("error_message"),
        )


@dataclass
class PMInfo:
    """Information about a package manager plugin.

    Used for plugin registration. Each PM plugin returns this
    to describe itself to the plugin system.

    Attributes:
        name: Package manager name (e.g., 'uv', 'pip')
        ecosystem: Package ecosystem (e.g., 'python', 'javascript')
        description: Human-readable description
        supported_sources: List of data sources this PM supports (e.g., ['packse'])
        installed: Whether the package manager is installed and available
        version: Optional version of the package manager
    """

    name: str
    ecosystem: str
    description: str
    supported_sources: list[str]
    installed: bool = False
    version: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "PMInfo":
        """Create PMInfo from plugin dict.

        Args:
            d: Dict with PM info fields

        Returns:
            PMInfo instance
        """
        return cls(
            name=d["name"],
            ecosystem=d["ecosystem"],
            description=d["description"],
            supported_sources=d["supported_sources"],
            installed=d.get("installed", False),
            version=d.get("version"),
        )


@dataclass
class PackageManagerInfo:
    """Metadata about a package manager."""

    name: str
    """Package manager name (e.g., 'uv', 'pip', 'pnpm', 'gradle')"""

    display_name: str
    """Human-readable display name"""

    manifest_files: list[str]
    """List of manifest files this PM generates (e.g., ['pyproject.toml'])"""

    lock_files: list[str]
    """List of lock files this PM generates (e.g., ['uv.lock'])"""

    description: str = ""
    """Brief description of the package manager"""

    ecosystem: str = ""
    """Ecosystem (e.g., 'python', 'javascript', 'java')"""

    def __str__(self) -> str:
        """String representation."""
        return f"{self.display_name} ({self.name})"


# Predefined package manager metadata
UV_INFO = PackageManagerInfo(
    name="uv",
    display_name="UV",
    manifest_files=["pyproject.toml"],
    lock_files=["uv.lock"],
    description="Fast Python package manager and resolver",
    ecosystem="python",
)

PIP_INFO = PackageManagerInfo(
    name="pip",
    display_name="Pip",
    manifest_files=["pyproject.toml", "requirements.in"],
    lock_files=["requirements.txt"],
    description="Python package installer with pip-compile",
    ecosystem="python",
)

PNPM_INFO = PackageManagerInfo(
    name="pnpm",
    display_name="pnpm",
    manifest_files=["package.json"],
    lock_files=["pnpm-lock.yaml"],
    description="Fast, disk space efficient JavaScript package manager",
    ecosystem="javascript",
)

GRADLE_INFO = PackageManagerInfo(
    name="gradle",
    display_name="Gradle",
    manifest_files=["build.gradle", "build.gradle.kts"],
    lock_files=["gradle.lockfile"],
    description="Build automation tool for JVM languages",
    ecosystem="java",
)
