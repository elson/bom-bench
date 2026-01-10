"""Hook specifications for bom-bench plugins.

This module defines the hooks that plugins can implement to integrate
SCA tools and fixture sets with bom-bench. Plugins use the @hookimpl
decorator to implement these hooks.

Example plugin implementation:

    from bom_bench import hookimpl

    @hookimpl
    def register_sca_tools():
        return {
            "name": "my-tool",
            "description": "My custom SCA tool",
            "supported_ecosystems": ["python"],
            "tools": [{"name": "node", "version": "22"}],
            "command": "my-tool",
            "args": ["scan", "${PROJECT_DIR}", "-o", "${OUTPUT_PATH}"],
            "env": {"API_KEY": "${MY_API_KEY:-}"},
        }
"""

from types import ModuleType

import pluggy

hookspec = pluggy.HookspecMarker("bom_bench")


class FixtureSetSpec:
    """Hook specifications for fixture set plugins.

    Plugins implement these hooks to provide test fixtures for benchmarking.
    Each fixture set contains a collection of test cases with shared environment
    configuration.
    """

    @hookspec
    def register_fixture_sets(
        self,
        bom_bench: ModuleType,
    ) -> list[dict]:  # type: ignore[empty-body]
        """Register fixture sets provided by this plugin.

        Called during fixture discovery to collect all available fixture sets.
        Each plugin returns a list of dicts describing the fixture sets it provides.

        Args:
            bom_bench: The bom_bench module with helper functions for dependency injection

        Returns:
            List of dicts with fixture set info:
                - name: Fixture set identifier (required)
                - description: Human-readable description (required)
                - ecosystem: Package ecosystem, e.g., "python" (required)
                - environment: Dict with mise configuration:
                    - tools: List of {name, version} dicts
                    - env: Dict of environment variables
                    - registry_url: Optional package registry URL
                - fixtures: List of fixture dicts:
                    - name: Fixture identifier
                    - files: Dict with paths (manifest, lock_file, expected_sbom, meta)
                    - satisfiable: Whether the fixture is satisfiable
                    - description: Optional description

        Example implementation:
            @hookimpl
            def register_fixture_sets(bom_bench):
                return [{
                    "name": "packse",
                    "description": "Python dependency resolution scenarios",
                    "ecosystem": "python",
                    "environment": {
                        "tools": [
                            {"name": "uv", "version": "0.5.11"},
                            {"name": "python", "version": "3.12"},
                        ],
                        "env": {},
                        "registry_url": "http://localhost:3141/simple-html",
                    },
                    "fixtures": [
                        {
                            "name": "fork-basic",
                            "files": {
                                "manifest": "/path/to/pyproject.toml",
                                "lock_file": "/path/to/uv.lock",
                                "expected_sbom": "/path/to/expected.cdx.json",
                                "meta": "/path/to/meta.json",
                            },
                            "satisfiable": True,
                            "description": "Basic fork scenario",
                        }
                    ],
                }]
        """
        ...


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
                - description: Human-readable description
                - supported_ecosystems: List of ecosystems (e.g., ["python", "javascript"])
                - homepage: Tool homepage URL
                - tools: List of mise tool dependencies (e.g., [{"name": "node", "version": "22"}])
                - command: Command to execute (e.g., "cdxgen", "syft")
                - args: List of arguments with ${var} placeholders (e.g., ["-o", "${OUTPUT_PATH}"])
                - env: Dict of environment variables (supports ${VAR} and ${VAR:-default} syntax)

        Example implementation:
            @hookimpl
            def register_sca_tools():
                return {
                    "name": "cdxgen",
                    "description": "CycloneDX generator",
                    "supported_ecosystems": ["python", "javascript", "java"],
                    "tools": [{"name": "npm:@cyclonedx/cdxgen", "version": "11.11"}],
                    "command": "cdxgen",
                    "args": ["-o", "${OUTPUT_PATH}", "${PROJECT_DIR}"],
                    "env": {},
                }
        """
        ...

    @hookspec
    def handle_sca_tool_response(
        self,
        bom_bench: ModuleType,
        stdout: str,
        stderr: str,
        output_file_contents: str | None,
    ) -> str | None:  # type: ignore[empty-body]
        """Parse SCA tool response and return CycloneDX 1.6 JSON SBOM.

        Optional hook for SCA tool plugins to parse non-CycloneDX tool output
        and convert it to CycloneDX 1.6 JSON format.

        This hook is called directly on the plugin module that registered the
        tool (not via pm.hook), so only the specific tool's plugin is invoked.

        Args:
            bom_bench: The bom_bench module with helper functions:
                - generate_cyclonedx_sbom(scenario_name, expected_packages): Creates CycloneDX SBOM
            stdout: Standard output from the SCA tool execution
            stderr: Standard error from the SCA tool execution
            output_file_contents: Contents of the default output file if generated,
                                  or None if no output file was created

        Returns:
            CycloneDX 1.6 JSON SBOM as a string, or None to use default behavior
            (keep the tool's original output file unchanged)

        Example implementation:
            @hookimpl
            def handle_sca_tool_response(bom_bench, stdout, stderr, output_file_contents):
                # Parse custom tool output (e.g., from stdout or custom format file)
                packages = parse_my_tool_output(stdout)

                # Generate CycloneDX SBOM using bom_bench helper
                sbom = bom_bench.generate_cyclonedx_sbom("project", packages)
                return json.dumps(sbom, indent=2)
        """
        ...


class RendererSpec:
    """Hook specifications for result renderer plugins.

    Plugins implement these hooks to generate output files from benchmark results.
    """

    @hookspec
    def register_sca_tool_result_renderer(
        self,
        bom_bench: ModuleType,
        tool_name: str,
        summaries: list[dict],
    ) -> dict | None:  # type: ignore[empty-body]
        """Render results for a single SCA tool.

        Called after benchmarking completes for a specific SCA tool.
        Generates output files written to output/benchmarks/{tool_name}/.

        Args:
            bom_bench: The bom_bench module with helper functions
            tool_name: Name of the SCA tool
            summaries: List of BenchmarkSummary dicts (one per fixture set)
                Each summary contains:
                - fixture_set: Name of fixture set
                - tool_name: SCA tool name
                - total_scenarios: Total fixtures run
                - successful/sbom_failed/unsatisfiable: Status counts
                - mean/median metrics: Precision, recall, F1
                - results: List of BenchmarkResult dicts with metrics

        Returns:
            Dict with 'filename' and 'content' keys, or None to skip rendering.
            The file will be written to output/benchmarks/{tool_name}/{filename}

        Example implementation:
            @hookimpl
            def register_sca_tool_result_renderer(tool_name, summaries):
                output = {"tool": tool_name, "fixture_sets": summaries}
                return {
                    "filename": "results.json",
                    "content": json.dumps(output, indent=2),
                }
        """
        ...

    @hookspec
    def register_benchmark_result_renderer(
        self,
        bom_bench: ModuleType,
        overall_summaries: list[dict],
        summaries: list[dict],
    ) -> dict | None:  # type: ignore[empty-body]
        """Render aggregate results for entire benchmark run.

        Called after all benchmarks complete across all tools.
        Generates output files written to output/benchmarks/.

        Args:
            bom_bench: The bom_bench module with helper functions
            overall_summaries: List of BenchmarkOverallSummary dicts (one per tool)
                Each contains pre-computed aggregated metrics across all fixture sets:
                - tool_name: SCA tool name
                - fixture_sets: Number of fixture sets
                - total_scenarios: Total across all fixture sets
                - successful: Total successful scenarios
                - mean_precision/recall/f1_score: Aggregated means
                - median_precision/recall/f1_score: Aggregated medians
            summaries: List of all BenchmarkSummary dicts (all tools, all fixture sets)
                Each contains detailed results with individual scenario metrics.
                Use this for detailed renderers that need per-scenario data.

        Returns:
            Dict with 'filename' and 'content' keys, or None to skip rendering.
            The file will be written to output/benchmarks/{filename}

        Example implementation:
            @hookimpl
            def register_benchmark_result_renderer(overall_summaries):
                # All aggregation already done, just format
                data = {"tools": {s["tool_name"]: s for s in overall_summaries}}
                return {
                    "filename": "benchmark_results.csv",
                    "content": format_as_csv(data),
                }
        """
        ...
