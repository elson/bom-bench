"""Package manager metadata models."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


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
    Replaces LockResult for the simplified PM plugin interface.

    Attributes:
        pm_name: Package manager name
        status: Processing status
        manifest_path: Path to generated manifest file
        lock_file_path: Path to lock file
        sbom_path: Path to generated SBOM (expected.cdx.json)
        meta_path: Path to meta.json file
        duration_seconds: Processing duration in seconds
        exit_code: Exit code from lock command
        error_message: Error message if failed
    """

    pm_name: str
    status: ProcessStatus
    duration_seconds: float
    exit_code: int
    manifest_path: Path | None = None
    lock_file_path: Path | None = None
    sbom_path: Path | None = None
    meta_path: Path | None = None
    error_message: str | None = None

    @classmethod
    def success(
        cls,
        pm_name: str,
        manifest_path: Path,
        lock_file_path: Path,
        sbom_path: Path,
        meta_path: Path,
        duration_seconds: float,
        exit_code: int,
    ) -> "ProcessScenarioResult":
        """Create a successful result.

        Args:
            pm_name: Package manager name
            manifest_path: Path to manifest file
            lock_file_path: Path to lock file
            sbom_path: Path to SBOM file
            meta_path: Path to meta.json
            duration_seconds: Processing duration
            exit_code: Exit code

        Returns:
            ProcessScenarioResult with SUCCESS status
        """
        return cls(
            pm_name=pm_name,
            status=ProcessStatus.SUCCESS,
            manifest_path=manifest_path,
            lock_file_path=lock_file_path,
            sbom_path=sbom_path,
            meta_path=meta_path,
            duration_seconds=duration_seconds,
            exit_code=exit_code,
        )

    @classmethod
    def failed(
        cls,
        pm_name: str,
        duration_seconds: float,
        exit_code: int,
        error_message: str,
    ) -> "ProcessScenarioResult":
        """Create a failed result.

        Args:
            pm_name: Package manager name
            duration_seconds: Processing duration
            exit_code: Exit code
            error_message: Error message

        Returns:
            ProcessScenarioResult with FAILED status
        """
        return cls(
            pm_name=pm_name,
            status=ProcessStatus.FAILED,
            duration_seconds=duration_seconds,
            exit_code=exit_code,
            error_message=error_message,
        )

    @classmethod
    def unsatisfiable(
        cls,
        pm_name: str,
        manifest_path: Path,
        meta_path: Path,
        duration_seconds: float,
        exit_code: int,
    ) -> "ProcessScenarioResult":
        """Create an unsatisfiable result.

        Args:
            pm_name: Package manager name
            manifest_path: Path to manifest file
            meta_path: Path to meta.json
            duration_seconds: Processing duration
            exit_code: Exit code

        Returns:
            ProcessScenarioResult with UNSATISFIABLE status
        """
        return cls(
            pm_name=pm_name,
            status=ProcessStatus.UNSATISFIABLE,
            manifest_path=manifest_path,
            meta_path=meta_path,
            duration_seconds=duration_seconds,
            exit_code=exit_code,
        )

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
            manifest_path=Path(d["manifest_path"]) if d.get("manifest_path") else None,
            lock_file_path=Path(d["lock_file_path"]) if d.get("lock_file_path") else None,
            sbom_path=Path(d["sbom_path"]) if d.get("sbom_path") else None,
            meta_path=Path(d["meta_path"]) if d.get("meta_path") else None,
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
