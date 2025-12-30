"""Processing result models."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import click

from bom_bench.logging_config import get_logger

logger = get_logger(__name__)


class ProcessingStatus(Enum):
    """Status of scenario processing."""

    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


class LockStatus(Enum):
    """Status of lock file generation."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ProcessingResult:
    """Result of processing a single scenario."""

    scenario_name: str
    """Name of the scenario that was processed"""

    status: ProcessingStatus
    """Processing status"""

    package_manager: str
    """Package manager used (e.g., 'uv', 'pip')"""

    output_dir: Path | None = None
    """Directory where output was generated"""

    error_message: str | None = None
    """Error message if processing failed"""


@dataclass
class LockResult:
    """Result of lock file generation."""

    scenario_name: str
    """Name of the scenario"""

    package_manager: str
    """Package manager used for locking"""

    status: LockStatus
    """Lock generation status"""

    exit_code: int | None = None
    """Exit code from lock command"""

    stdout: str | None = None
    """Standard output from lock command"""

    stderr: str | None = None
    """Standard error from lock command"""

    lock_file: Path | None = None
    """Path to generated lock file (e.g., uv.lock, requirements.txt)"""

    error_message: str | None = None
    """Error message if lock failed"""

    duration_seconds: float | None = None
    """Time taken to generate lock file"""


@dataclass
class Summary:
    """Summary statistics for a processing run."""

    total_scenarios: int
    """Total number of scenarios found"""

    processed: int = 0
    """Number of scenarios successfully processed"""

    skipped: int = 0
    """Number of scenarios skipped (filtered out)"""

    failed: int = 0
    """Number of scenarios that failed processing"""

    package_manager: str | None = None
    """Package manager used (None if multiple)"""

    data_source: str | None = None
    """Data source used (None if multiple)"""

    def add_processing_result(self, result: ProcessingResult) -> None:
        """Add a processing result to the summary.

        Args:
            result: Processing result to add
        """
        if result.status == ProcessingStatus.SUCCESS:
            self.processed += 1
        elif result.status == ProcessingStatus.SKIPPED:
            self.skipped += 1
        elif result.status == ProcessingStatus.FAILED:
            self.failed += 1

    def print_summary(self) -> None:
        """Print a formatted summary with colored output."""
        logger.info("")
        logger.info(click.style("Summary:", bold=True))
        logger.info(f"  Processed: {click.style(str(self.processed), fg='green')}")
        logger.info(f"  Skipped: {self.skipped}")
        if self.failed > 0:
            logger.warning(f"  Failed: {click.style(str(self.failed), fg='red')}")
        logger.info(f"  Total: {self.total_scenarios}")
