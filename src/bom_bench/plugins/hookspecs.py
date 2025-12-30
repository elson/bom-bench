"""Hook specifications for bom-bench plugins.

This module defines the hooks that plugins can implement to integrate
SCA tools and package managers with bom-bench. Plugins use the @hookimpl
decorator to implement these hooks.

Example plugin implementation:

    from bom_bench import hookimpl

    @hookimpl
    def register_sca_tools():
        return {
            "name": "my-tool",
            "description": "My custom SCA tool",
            "supported_ecosystems": ["python"],
            "installed": shutil.which("my-tool") is not None
        }
"""

from pathlib import Path
from types import ModuleType
from typing import Any

import pluggy

hookspec = pluggy.HookspecMarker("bom_bench")


class SCAToolSpec:
    """Hook specifications for SCA tool plugins.

    Plugins implement these hooks to integrate SCA tools with bom-bench.
    Each hook uses Pluggy's dependency injection - plugins only need to
    declare the parameters they actually use.
    """

    @hookspec
    def register_sca_tools(self) -> dict:  # type: ignore[empty-body]
        """Register an SCA tool provided by this plugin.

        Called during plugin discovery to collect all available SCA tools.
        Each plugin returns a single dict describing the tool it provides.

        Returns:
            Dict with tool info:
                - name: Tool identifier (required)
                - version: Tool version string
                - description: Human-readable description
                - supported_ecosystems: List of ecosystems (e.g., ["python", "javascript"])
                - homepage: Tool homepage URL
                - installed: Whether the tool is installed (required)

        Example implementation:
            @hookimpl
            def register_sca_tools():
                return {
                    "name": "cdxgen",
                    "version": _get_cdxgen_version(),
                    "description": "CycloneDX generator",
                    "supported_ecosystems": ["python", "javascript", "java"],
                    "installed": shutil.which("cdxgen") is not None
                }
        """
        ...

    @hookspec
    def scan_project(
        self,
        tool_name: str,
        project_dir: Path,
        output_path: Path,
        ecosystem: str,
        timeout: int = 120,
    ) -> dict | None:
        """Scan a project using the specified tool to generate SBOM.

        This is the core hook - plugins invoke their tool and return results.
        bom-bench handles all comparison, metrics, and reporting.

        Args:
            tool_name: Name of the tool to use (e.g., "cdxgen")
            project_dir: Directory containing manifest/lock files to scan
            output_path: Where to write the generated SBOM
            ecosystem: Package ecosystem (e.g., "python", "javascript")
            timeout: Maximum execution time in seconds

        Returns:
            Dict with result info:
                - tool_name: Tool name
                - status: "success", "tool_failed", "timeout", "parse_error", "tool_not_found"
                - sbom_path: Path to generated SBOM (on success)
                - duration_seconds: Execution time
                - exit_code: Tool exit code
                - error_message: Error message (on failure)
            None if this plugin doesn't handle this tool.

        Example implementation:
            @hookimpl
            def scan_project(tool_name, project_dir, output_path, timeout):
                if tool_name != "cdxgen":
                    return None
                # Run cdxgen subprocess
                return {
                    "tool_name": "cdxgen",
                    "status": "success",
                    "sbom_path": str(output_path),
                    "duration_seconds": 1.5,
                    "exit_code": 0
                }
        """


class PackageManagerSpec:
    """Hook specifications for package manager plugins.

    Plugins implement these hooks to integrate package managers with bom-bench.
    Each PM plugin is responsible for loading its scenarios, generating manifests,
    and running lock commands.
    """

    @hookspec
    def register_package_managers(self) -> dict:  # type: ignore[empty-body]
        """Register a package manager provided by this plugin.

        Called during plugin discovery to collect all available package managers.
        Each plugin returns a single dict describing the PM it provides.

        Returns:
            Dict with PM info:
                - name: Package manager identifier (required)
                - ecosystem: Package ecosystem (required)
                - description: Human-readable description (required)
                - supported_sources: List of data sources this PM supports (required)
                - installed: Whether the PM is installed (required)
                - version: PM version string (optional)

        Example implementation:
            @hookimpl
            def register_package_managers():
                return {
                    "name": "uv",
                    "ecosystem": "python",
                    "description": "Fast Python package manager",
                    "supported_sources": ["packse"],
                    "installed": shutil.which("uv") is not None,
                    "version": _get_uv_version()
                }
        """
        ...

    @hookspec
    def process_scenario(
        self,
        pm_name: str,
        scenario: dict[str, Any],
        output_dir: Path,
        bom_bench: ModuleType,
        timeout: int = 120,
    ) -> dict | None:
        """Process a scenario: generate manifest, lock, and SBOM.

        Plugins receive the bom_bench module for dependency injection,
        allowing access to helper functions without direct imports.

        Args:
            pm_name: Package manager name (e.g., "uv")
            scenario: Scenario as dict (converted from Scenario dataclass)
            output_dir: Scenario output directory (where files should be written)
            bom_bench: The bom_bench module with helper functions:
                - bom_bench.generate_sbom_file(scenario_name, output_path, packages)
                - bom_bench.generate_meta_file(output_path, satisfiable, exit_code, stdout, stderr)
                - bom_bench.get_logger(name)
            timeout: Maximum execution time in seconds

        Returns:
            Dict with result info:
                - pm_name: Package manager name
                - status: "success", "failed", "timeout", "unsatisfiable"
                - duration_seconds: Processing duration
                - exit_code: Exit code from lock command
                - error_message: Error message (on failure)
            None if this plugin doesn't handle this PM.

        Example implementation:
            @hookimpl
            def process_scenario(pm_name, scenario, output_dir, bom_bench, timeout=120):
                if pm_name != "uv":
                    return None
                # Access scenario as dict
                name = scenario["name"]
                packages = scenario["expected"]["packages"]

                # Use helper functions from bom_bench module
                bom_bench.generate_sbom_file(name, output_dir / "expected.cdx.json", packages)
                bom_bench.generate_meta_file(output_dir / "meta.json", True, 0, "", "")

                return {
                    "pm_name": "uv",
                    "status": "success",
                    "duration_seconds": 1.5,
                    "exit_code": 0
                }
        """
