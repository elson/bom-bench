"""Processing result models."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from pathlib import Path


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

    output_dir: Optional[Path] = None
    """Directory where output was generated"""

    error_message: Optional[str] = None
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

    exit_code: Optional[int] = None
    """Exit code from lock command"""

    output_file: Optional[Path] = None
    """Path to lock output log file"""

    lock_file: Optional[Path] = None
    """Path to generated lock file (e.g., uv.lock, requirements.txt)"""

    error_message: Optional[str] = None
    """Error message if lock failed"""

    duration_seconds: Optional[float] = None
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

    lock_success: int = 0
    """Number of successful lock file generations"""

    lock_failed: int = 0
    """Number of failed lock file generations"""

    package_manager: Optional[str] = None
    """Package manager used (None if multiple)"""

    data_source: Optional[str] = None
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

    def add_lock_result(self, result: LockResult) -> None:
        """Add a lock result to the summary.

        Args:
            result: Lock result to add
        """
        if result.status == LockStatus.SUCCESS:
            self.lock_success += 1
        else:
            self.lock_failed += 1

    def print_summary(self, include_lock: bool = False) -> None:
        """Print a formatted summary.

        Args:
            include_lock: Whether to include lock statistics
        """
        print(f"\nGeneration Summary:")
        print(f"  Processed: {self.processed}")
        print(f"  Skipped: {self.skipped}")
        if self.failed > 0:
            print(f"  Failed: {self.failed}")
        print(f"  Total: {self.total_scenarios}")

        if include_lock:
            print(f"\nLock Summary:")
            print(f"  Success: {self.lock_success}")
            print(f"  Failed: {self.lock_failed}")
            print(f"  Total: {self.lock_success + self.lock_failed}")
