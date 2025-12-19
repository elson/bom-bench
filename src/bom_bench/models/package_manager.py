"""Package manager metadata models."""

from dataclasses import dataclass
from typing import List


@dataclass
class PackageManagerInfo:
    """Metadata about a package manager."""

    name: str
    """Package manager name (e.g., 'uv', 'pip', 'pnpm', 'gradle')"""

    display_name: str
    """Human-readable display name"""

    manifest_files: List[str]
    """List of manifest files this PM generates (e.g., ['pyproject.toml'])"""

    lock_files: List[str]
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
    ecosystem="python"
)

PIP_INFO = PackageManagerInfo(
    name="pip",
    display_name="Pip",
    manifest_files=["pyproject.toml", "requirements.in"],
    lock_files=["requirements.txt"],
    description="Python package installer with pip-compile",
    ecosystem="python"
)

PNPM_INFO = PackageManagerInfo(
    name="pnpm",
    display_name="pnpm",
    manifest_files=["package.json"],
    lock_files=["pnpm-lock.yaml"],
    description="Fast, disk space efficient JavaScript package manager",
    ecosystem="javascript"
)

GRADLE_INFO = PackageManagerInfo(
    name="gradle",
    display_name="Gradle",
    manifest_files=["build.gradle", "build.gradle.kts"],
    lock_files=["gradle.lockfile"],
    description="Build automation tool for JVM languages",
    ecosystem="java"
)
