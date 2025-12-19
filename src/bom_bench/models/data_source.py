"""Data source metadata models."""

from dataclasses import dataclass
from typing import List


@dataclass
class DataSourceInfo:
    """Metadata about a data source."""

    name: str
    """Data source name (e.g., 'packse', 'pnpm-tests')"""

    display_name: str
    """Human-readable display name"""

    supported_pms: List[str]
    """List of package managers this source supports (e.g., ['uv', 'pip'])"""

    description: str = ""
    """Brief description of the data source"""

    url: str = ""
    """URL to the data source repository or documentation"""

    def __str__(self) -> str:
        """String representation."""
        pms = ", ".join(self.supported_pms)
        return f"{self.display_name} ({self.name}) - supports: {pms}"


# Predefined data source metadata
PACKSE_INFO = DataSourceInfo(
    name="packse",
    display_name="Packse",
    supported_pms=["uv", "pip"],
    description="Python packaging scenarios for testing dependency resolution",
    url="https://github.com/zanieb/packse"
)

PNPM_TESTS_INFO = DataSourceInfo(
    name="pnpm-tests",
    display_name="pnpm Test Cases",
    supported_pms=["pnpm"],
    description="Test cases from the pnpm repository",
    url="https://github.com/pnpm/pnpm"
)

GRADLE_TESTKIT_INFO = DataSourceInfo(
    name="gradle-testkit",
    display_name="Gradle TestKit",
    supported_pms=["gradle"],
    description="Gradle dependency resolution test scenarios",
    url="https://github.com/gradle/gradle"
)
