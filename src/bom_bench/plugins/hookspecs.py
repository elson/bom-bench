"""Hook specifications for bom-bench plugins.

This module defines the hooks that plugins can implement to integrate
SCA tools and package managers with bom-bench. Plugins use the @hookimpl
decorator to implement these hooks.

Example plugin implementation:

    import pluggy
    from bom_bench.models.sca import SCAToolInfo, SBOMResult

    hookimpl = pluggy.HookimplMarker("bom_bench")

    @hookimpl
    def register_sca_tools():
        return [
            SCAToolInfo(
                name="my-tool",
                description="My custom SCA tool",
                supported_ecosystems=["python"]
            )
        ]
"""

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import pluggy

if TYPE_CHECKING:
    from bom_bench.models.sca import SCAToolInfo, SBOMResult
    from bom_bench.models.package_manager import PMInfo
    from bom_bench.models.scenario import Scenario
    from bom_bench.models.result import LockResult

hookspec = pluggy.HookspecMarker("bom_bench")


class SCAToolSpec:
    """Hook specifications for SCA tool plugins.

    Plugins implement these hooks to integrate SCA tools with bom-bench.
    Each hook uses Pluggy's dependency injection - plugins only need to
    declare the parameters they actually use.
    """

    @hookspec
    def register_sca_tools(self) -> List["SCAToolInfo"]:
        """Register SCA tools provided by this plugin.

        Called during plugin discovery to collect all available SCA tools.
        A single plugin may register multiple tools.

        Returns:
            List of SCAToolInfo describing each tool this plugin provides.

        Example implementation:
            @hookimpl
            def register_sca_tools():
                return [
                    SCAToolInfo(
                        name="cdxgen",
                        version="10.x",
                        description="CycloneDX generator",
                        supported_ecosystems=["python", "javascript", "java"],
                    )
                ]
        """

    @hookspec
    def check_tool_available(self, tool_name: str) -> Optional[bool]:
        """Check if a specific tool is available/installed.

        Args:
            tool_name: Name of the tool to check (e.g., "cdxgen")

        Returns:
            True if tool is available and ready to use.
            False if tool is not available.
            None if this plugin doesn't handle this tool.

        Example implementation:
            @hookimpl
            def check_tool_available(tool_name):
                if tool_name != "cdxgen":
                    return None
                return shutil.which("cdxgen") is not None
        """

    @hookspec
    def generate_sbom(
        self,
        tool_name: str,
        project_dir: Path,
        output_path: Path,
        ecosystem: str,
        timeout: int = 120
    ) -> Optional["SBOMResult"]:
        """Generate SBOM for a project using the specified tool.

        This is the core hook - plugins invoke their tool and return results.
        bom-bench handles all comparison, metrics, and reporting.

        Args:
            tool_name: Name of the tool to use (e.g., "cdxgen")
            project_dir: Directory containing manifest/lock files to scan
            output_path: Where to write the generated SBOM
            ecosystem: Package ecosystem (e.g., "python", "javascript")
            timeout: Maximum execution time in seconds

        Returns:
            SBOMResult with execution details and SBOM path.
            None if this plugin doesn't handle this tool.

        Example implementation:
            @hookimpl
            def generate_sbom(tool_name, project_dir, output_path, timeout):
                if tool_name != "cdxgen":
                    return None
                # Run cdxgen subprocess
                # Return SBOMResult.success() or SBOMResult.failed()
        """


class PackageManagerSpec:
    """Hook specifications for package manager plugins.

    Plugins implement these hooks to integrate package managers with bom-bench.
    Each PM plugin is responsible for loading its scenarios, generating manifests,
    and running lock commands.
    """

    @hookspec
    def register_package_managers(self) -> List["PMInfo"]:
        """Register package managers provided by this plugin.

        Called during plugin discovery to collect all available package managers.

        Returns:
            List of PMInfo describing each package manager this plugin provides.

        Example implementation:
            @hookimpl
            def register_package_managers():
                return [
                    PMInfo(
                        name="uv",
                        ecosystem="python",
                        description="UV Python package manager",
                        data_source="packse"
                    )
                ]
        """

    @hookspec
    def load_scenarios(
        self,
        pm_name: str,
        data_dir: Path
    ) -> Optional[List["Scenario"]]:
        """Load scenarios for a package manager.

        Args:
            pm_name: Package manager name (e.g., "uv")
            data_dir: Base data directory

        Returns:
            List of scenarios, or None if not handled by this plugin.

        Example implementation:
            @hookimpl
            def load_scenarios(pm_name, data_dir):
                if pm_name != "uv":
                    return None
                # Load and return packse scenarios
        """

    @hookspec
    def generate_manifest(
        self,
        pm_name: str,
        scenario: "Scenario",
        output_dir: Path
    ) -> Optional[Path]:
        """Generate manifest file for a scenario.

        Args:
            pm_name: Package manager name
            scenario: Scenario to generate manifest for
            output_dir: Output directory

        Returns:
            Path to manifest file, or None if not handled.

        Example implementation:
            @hookimpl
            def generate_manifest(pm_name, scenario, output_dir):
                if pm_name != "uv":
                    return None
                # Generate pyproject.toml and return path
        """

    @hookspec
    def run_lock(
        self,
        pm_name: str,
        project_dir: Path,
        scenario_name: str,
        timeout: int = 120
    ) -> Optional["LockResult"]:
        """Run lock command for a project.

        Args:
            pm_name: Package manager name
            project_dir: Directory containing manifest
            scenario_name: Name of scenario
            timeout: Timeout in seconds

        Returns:
            LockResult, or None if not handled.

        Example implementation:
            @hookimpl
            def run_lock(pm_name, project_dir, scenario_name, timeout):
                if pm_name != "uv":
                    return None
                # Run uv lock and return LockResult
        """

    @hookspec
    def check_pm_available(self, pm_name: str) -> Optional[bool]:
        """Check if a specific package manager is available/installed.

        Args:
            pm_name: Name of the package manager to check (e.g., "uv")

        Returns:
            True if PM is available and ready to use.
            False if PM is not available.
            None if this plugin doesn't handle this PM.
        """

    @hookspec
    def get_output_dir(
        self,
        pm_name: str,
        base_dir: Path,
        scenario_name: str
    ) -> Optional[Path]:
        """Get output directory for a scenario.

        Args:
            pm_name: Package manager name
            base_dir: Base output directory
            scenario_name: Name of the scenario

        Returns:
            Path to scenario output directory, or None if not handled.

        Example implementation:
            @hookimpl
            def get_output_dir(pm_name, base_dir, scenario_name):
                if pm_name != "uv":
                    return None
                return base_dir / "scenarios" / "uv" / scenario_name
        """

    @hookspec
    def validate_scenario(
        self,
        pm_name: str,
        scenario: "Scenario"
    ) -> Optional[bool]:
        """Check if a scenario is compatible with a package manager.

        Args:
            pm_name: Package manager name
            scenario: Scenario to validate

        Returns:
            True if compatible, False if not, None if not handled.

        Example implementation:
            @hookimpl
            def validate_scenario(pm_name, scenario):
                if pm_name != "uv":
                    return None
                return scenario.source in ["packse"]
        """

    @hookspec
    def generate_sbom_for_lock(
        self,
        pm_name: str,
        scenario: "Scenario",
        output_dir: Path,
        lock_result: "LockResult"
    ) -> Optional[Path]:
        """Generate SBOM and meta files from lock result.

        Args:
            pm_name: Package manager name
            scenario: Scenario being processed
            output_dir: Scenario output directory
            lock_result: Result of lock operation

        Returns:
            Path to generated SBOM file, or None if not handled.

        Example implementation:
            @hookimpl
            def generate_sbom_for_lock(pm_name, scenario, output_dir, lock_result):
                if pm_name != "uv":
                    return None
                # Generate meta.json and expected.cdx.json
        """
