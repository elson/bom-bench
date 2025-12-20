"""SCA tool runner for benchmarking (STUB - Not yet implemented).

This module will run SCA (Software Composition Analysis) tools against
generated package manager outputs and collect vulnerability findings.

Supported SCA Tools (planned):
- Grype (https://github.com/anchore/grype)
- Trivy (https://github.com/aquasecurity/trivy)
- Snyk (https://snyk.io/)
- OSV-Scanner (https://github.com/google/osv-scanner)

Implementation TODO:
- Define SCAToolRunner ABC interface
- Implement tool-specific runners (GrypeRunner, TrivyRunner, etc.)
- Handle tool installation/availability checks
- Execute tools against generated outputs
- Parse and normalize results
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum


class SCAToolType(Enum):
    """Supported SCA tool types."""

    GRYPE = "grype"
    TRIVY = "trivy"
    SNYK = "snyk"
    OSV_SCANNER = "osv-scanner"


class SCAToolRunner(ABC):
    """Abstract base class for SCA tool runners (STUB).

    Each SCA tool implementation should inherit from this class
    and implement the run() method to execute the tool and parse results.
    """

    tool_name: str
    """Name of the SCA tool"""

    @abstractmethod
    def check_available(self) -> bool:
        """Check if the SCA tool is installed and available.

        Returns:
            True if tool is available, False otherwise
        """
        pass

    @abstractmethod
    def run(
        self,
        project_dir: Path,
        package_manager: str,
        scenario_name: str
    ) -> Dict[str, Any]:
        """Run the SCA tool against a project directory.

        Args:
            project_dir: Directory containing lock files to scan
            package_manager: Package manager name (uv, pip, pnpm, gradle)
            scenario_name: Name of the scenario being scanned

        Returns:
            Dictionary with scan results (normalized format)

        Raises:
            NotImplementedError: This is a stub implementation
        """
        pass


class BenchmarkRunner:
    """Orchestrates benchmarking across multiple SCA tools and PMs (STUB).

    This class coordinates:
    - Running multiple SCA tools
    - Across multiple package managers
    - Against all generated scenarios
    - Collecting and normalizing results
    """

    def __init__(
        self,
        output_dir: Path,
        tools: Optional[List[SCAToolType]] = None,
        package_managers: Optional[List[str]] = None
    ):
        """Initialize benchmark runner.

        Args:
            output_dir: Base output directory with generated projects
            tools: List of SCA tools to run (default: all available)
            package_managers: List of PMs to benchmark (default: all)
        """
        self.output_dir = output_dir
        self.tools = tools or list(SCAToolType)
        self.package_managers = package_managers or ["uv", "pip", "pnpm", "gradle"]
        self.runners: Dict[SCAToolType, SCAToolRunner] = {}

    def run_benchmarks(self) -> Dict[str, Any]:
        """Run all benchmarks and collect results.

        Returns:
            Dictionary with comprehensive benchmark results

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "Benchmarking is not yet implemented. "
            "See src/bom_bench/benchmarking/runner.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. For each package manager in self.package_managers:
        #    a. Find all scenario directories in output/{pm}/
        #    b. For each scenario:
        #       - For each SCA tool in self.tools:
        #         * Check if tool is available
        #         * Run tool against scenario directory
        #         * Collect results
        # 2. Aggregate results across tools and PMs
        # 3. Return comprehensive result dictionary


# Stub implementations for specific SCA tools

class GrypeRunner(SCAToolRunner):
    """Grype SCA tool runner (STUB)."""

    tool_name = "grype"

    def check_available(self) -> bool:
        """Check if Grype is installed."""
        raise NotImplementedError("Grype runner not yet implemented")

    def run(
        self,
        project_dir: Path,
        package_manager: str,
        scenario_name: str
    ) -> Dict[str, Any]:
        """Run Grype scan."""
        raise NotImplementedError("Grype runner not yet implemented")

        # TODO: Run: grype dir:{project_dir} -o json


class TrivyRunner(SCAToolRunner):
    """Trivy SCA tool runner (STUB)."""

    tool_name = "trivy"

    def check_available(self) -> bool:
        """Check if Trivy is installed."""
        raise NotImplementedError("Trivy runner not yet implemented")

    def run(
        self,
        project_dir: Path,
        package_manager: str,
        scenario_name: str
    ) -> Dict[str, Any]:
        """Run Trivy scan."""
        raise NotImplementedError("Trivy runner not yet implemented")

        # TODO: Run: trivy fs {project_dir} --format json
