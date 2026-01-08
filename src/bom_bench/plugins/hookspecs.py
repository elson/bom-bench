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
