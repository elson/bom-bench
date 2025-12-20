"""Result collectors and normalizers for SCA benchmarking (STUB - Not yet implemented).

This module collects and normalizes results from different SCA tools
into a standard format for comparison and reporting.

Implementation TODO:
- Define standard result format
- Parse tool-specific output formats
- Normalize vulnerability data across tools
- Aggregate results by package, PM, and tool
- Calculate accuracy metrics (true/false positives)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SeverityLevel(Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class VulnerabilityFinding:
    """Normalized vulnerability finding from an SCA tool (STUB).

    This is the standard format that all SCA tool results are normalized to.
    """

    package_name: str
    """Name of the vulnerable package"""

    package_version: str
    """Version of the vulnerable package"""

    vulnerability_id: str
    """CVE or vulnerability database ID"""

    severity: SeverityLevel
    """Normalized severity level"""

    description: Optional[str] = None
    """Vulnerability description"""

    fixed_version: Optional[str] = None
    """Version that fixes the vulnerability"""

    tool_name: Optional[str] = None
    """SCA tool that found this vulnerability"""


@dataclass
class ScanResult:
    """Results from scanning a single scenario with one tool (STUB)."""

    scenario_name: str
    """Name of the scenario scanned"""

    package_manager: str
    """Package manager used (uv, pip, pnpm, gradle)"""

    tool_name: str
    """SCA tool name"""

    findings: List[VulnerabilityFinding]
    """List of vulnerability findings"""

    scan_duration_seconds: float
    """Time taken to scan"""

    success: bool = True
    """Whether scan completed successfully"""

    error_message: Optional[str] = None
    """Error message if scan failed"""


class ResultCollector:
    """Collects and normalizes SCA tool results (STUB).

    This class handles:
    - Parsing tool-specific output formats
    - Normalizing to standard VulnerabilityFinding format
    - Aggregating results across multiple scans
    - Deduplicating findings
    """

    def __init__(self):
        """Initialize result collector."""
        self.results: List[ScanResult] = []

    def add_grype_result(
        self,
        scenario_name: str,
        package_manager: str,
        grype_output: Dict[str, Any],
        duration: float
    ) -> None:
        """Parse and add Grype scan results.

        Args:
            scenario_name: Scenario that was scanned
            package_manager: Package manager used
            grype_output: Raw JSON output from Grype
            duration: Scan duration in seconds

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "Result collection is not yet implemented. "
            "See src/bom_bench/benchmarking/collectors.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Parse grype_output JSON structure
        # 2. Extract matches/vulnerabilities
        # 3. For each vulnerability:
        #    a. Create VulnerabilityFinding
        #    b. Map Grype severity to SeverityLevel
        #    c. Extract package info, CVE, description
        # 4. Create ScanResult and add to self.results

    def add_trivy_result(
        self,
        scenario_name: str,
        package_manager: str,
        trivy_output: Dict[str, Any],
        duration: float
    ) -> None:
        """Parse and add Trivy scan results.

        Args:
            scenario_name: Scenario that was scanned
            package_manager: Package manager used
            trivy_output: Raw JSON output from Trivy
            duration: Scan duration in seconds

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "Result collection is not yet implemented. "
            "See src/bom_bench/benchmarking/collectors.py for implementation guide."
        )

        # TODO: Similar to add_grype_result but for Trivy format

    def get_all_results(self) -> List[ScanResult]:
        """Get all collected scan results.

        Returns:
            List of all ScanResult objects
        """
        return self.results

    def get_results_by_pm(self, package_manager: str) -> List[ScanResult]:
        """Get results filtered by package manager.

        Args:
            package_manager: Package manager to filter by

        Returns:
            List of ScanResult objects for the specified PM
        """
        return [r for r in self.results if r.package_manager == package_manager]

    def get_results_by_tool(self, tool_name: str) -> List[ScanResult]:
        """Get results filtered by SCA tool.

        Args:
            tool_name: Tool name to filter by

        Returns:
            List of ScanResult objects for the specified tool
        """
        return [r for r in self.results if r.tool_name == tool_name]

    def deduplicate_findings(self) -> List[VulnerabilityFinding]:
        """Deduplicate vulnerability findings across all results.

        Returns:
            List of unique VulnerabilityFinding objects

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "Result collection is not yet implemented. "
            "See src/bom_bench/benchmarking/collectors.py for implementation guide."
        )

        # TODO: Deduplicate by (package_name, package_version, vulnerability_id)
