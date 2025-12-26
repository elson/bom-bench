"""Hook specifications for SCA tool plugins.

This module defines the hooks that plugins can implement to integrate
SCA tools with bom-bench. Plugins use the @hookimpl decorator to
implement these hooks.

Example plugin implementation:

    import pluggy
    from bom_bench.models.sca import SCAToolInfo, SBOMResult

    hookimpl = pluggy.HookimplMarker("bom_bench")

    @hookimpl
    def bom_bench_register_sca_tools():
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

hookspec = pluggy.HookspecMarker("bom_bench")


class SCAToolSpec:
    """Hook specifications for SCA tool plugins.

    Plugins implement these hooks to integrate SCA tools with bom-bench.
    Each hook uses Pluggy's dependency injection - plugins only need to
    declare the parameters they actually use.
    """

    @hookspec
    def bom_bench_register_sca_tools(self) -> List["SCAToolInfo"]:
        """Register SCA tools provided by this plugin.

        Called during plugin discovery to collect all available SCA tools.
        A single plugin may register multiple tools.

        Returns:
            List of SCAToolInfo describing each tool this plugin provides.

        Example implementation:
            @hookimpl
            def bom_bench_register_sca_tools():
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
    def bom_bench_check_tool_available(self, tool_name: str) -> Optional[bool]:
        """Check if a specific tool is available/installed.

        Args:
            tool_name: Name of the tool to check (e.g., "cdxgen")

        Returns:
            True if tool is available and ready to use.
            False if tool is not available.
            None if this plugin doesn't handle this tool.

        Example implementation:
            @hookimpl
            def bom_bench_check_tool_available(tool_name):
                if tool_name != "cdxgen":
                    return None
                return shutil.which("cdxgen") is not None
        """

    @hookspec
    def bom_bench_generate_sbom(
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
            def bom_bench_generate_sbom(tool_name, project_dir, output_path, timeout):
                if tool_name != "cdxgen":
                    return None
                # Run cdxgen subprocess
                # Return SBOMResult.success() or SBOMResult.failed()
        """
