# Contributing to bom-bench

Thank you for your interest in contributing to bom-bench! This document provides guidelines for extending the project with new package managers and SCA tool integrations.

## Table of Contents

- [Development Setup](#development-setup)
- [Adding a New Package Manager Plugin](#adding-a-new-package-manager-plugin)
- [Adding a New SCA Tool Plugin](#adding-a-new-sca-tool-plugin)
- [Testing Guidelines](#testing-guidelines)
- [Code Style](#code-style)

## Development Setup

### Prerequisites

- Python >= 3.12
- UV or pip package manager
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/bom-bench
cd bom-bench

# Install in editable mode
uv pip install -e ".[dev]"

# Run tests to verify setup
uv run pytest tests/ -v
```

### Project Structure

```
src/bom_bench/
├── cli.py                  # CLI: benchmark, list-fixtures, list-tools
├── config.py               # Configuration constants
├── logging.py              # Logging configuration
├── plugins/
│   ├── __init__.py         # DEFAULT_PLUGINS, initialize_plugins()
│   └── hookspecs.py        # Hook specifications (FixtureSetSpec, SCAToolSpec)
├── fixtures/
│   ├── __init__.py         # Fixture loading utilities
│   ├── loader.py           # FixtureSetLoader with caching
│   └── packse.py           # Packse fixture set plugin (example)
├── sca_tools/
│   ├── __init__.py         # SCA wrapper functions, tool registry
│   ├── cdxgen.py           # CycloneDX generator plugin
│   └── syft.py             # Syft plugin
├── models/
│   ├── fixture.py          # FixtureSet, Fixture, FixtureFiles
│   ├── sandbox.py          # SandboxConfig, SandboxResult
│   ├── sca_tool.py         # SCAToolInfo, SCAToolConfig, PurlMetrics
│   └── scenario.py         # Scenario models (for packse integration)
├── sandbox/
│   ├── mise.py             # ToolSpec, generate_mise_toml(), MiseRunner
│   └── sandbox.py          # Sandbox context manager
├── runner/
│   ├── runner.py           # BenchmarkRunner orchestration
│   └── executor.py         # Single fixture+tool execution
├── benchmarking/
│   └── comparison.py       # PURL extraction, normalization, comparison
└── generators/sbom/
    └── cyclonedx.py        # SBOM generation utilities
```

## Adding a New Fixture Set Plugin

Fixture set plugins provide pre-generated test projects with expected SBOMs for benchmarking SCA tools.

### Step 1: Create Plugin File

Create `src/bom_bench/fixtures/{source_name}.py`:

```python
"""Fixture set plugin for {SOURCE_NAME}."""

from pathlib import Path

from bom_bench import hookimpl


@hookimpl
def register_fixture_sets(bom_bench) -> list[dict]:
    """Register fixture sets with dependency injection.

    The bom_bench module is injected to access utilities like:
    - bom_bench.fixtures.loader.FixtureSetLoader
    - bom_bench.generators.sbom.cyclonedx
    - Other helper functions

    Returns:
        List of fixture set dictionaries. Each dict will be converted
        to a FixtureSet dataclass by the framework.
    """
    # Define your fixture set's environment requirements
    # These tools will be installed via mise in the sandbox
    environment = {
        "tools": [
            {"name": "python", "version": "3.12"},
            {"name": "uv", "version": "0.5.11"},
        ],
        "env": {
            "UV_INDEX_URL": "http://localhost:3141/simple",
        },
        "registry_url": "http://localhost:3141",
    }

    # Load or generate your fixtures
    fixtures = []

    # Example: Load from a directory of test cases
    fixture_dir = Path(__file__).parent.parent.parent / "data" / "my-fixtures"

    for test_case_dir in fixture_dir.glob("*"):
        if not test_case_dir.is_dir():
            continue

        # Each fixture needs these files
        manifest = test_case_dir / "pyproject.toml"
        lock_file = test_case_dir / "uv.lock"
        expected_sbom = test_case_dir / "expected.cdx.json"
        meta = test_case_dir / "meta.json"

        # Check satisfiability from meta.json
        import json
        meta_data = json.loads(meta.read_text()) if meta.exists() else {}
        satisfiable = meta_data.get("satisfiable", True)

        fixtures.append({
            "name": test_case_dir.name,
            "files": {
                "manifest": manifest,
                "lock_file": lock_file if lock_file.exists() else None,
                "expected_sbom": expected_sbom if expected_sbom.exists() else None,
                "meta": meta if meta.exists() else None,
            },
            "satisfiable": satisfiable,
            "description": meta_data.get("description", ""),
        })

    return [{
        "name": "my-fixtures",
        "description": "My custom fixture set",
        "ecosystem": "python",
        "environment": environment,
        "fixtures": fixtures,
    }]
```

### Step 2: Add to DEFAULT_PLUGINS

Update `src/bom_bench/plugins/__init__.py`:

```python
DEFAULT_PLUGINS = (
    "bom_bench.fixtures.packse",
    "bom_bench.fixtures.{source_name}",  # Add your fixture set
    "bom_bench.sca_tools.cdxgen",
    "bom_bench.sca_tools.syft",
)
```

### Step 3: Add Tests

Create tests in `tests/unit/test_{source_name}_plugin.py`.

### Fixture Set Best Practices

1. **Caching**: Use `FixtureSetLoader` to cache generated fixtures and avoid regeneration
2. **Hash-based invalidation**: Cache is invalidated when source data changes
3. **Satisfiability**: Mark unsatisfiable fixtures in `meta.json` to skip SBOM comparison
4. **Ground truth**: Provide `expected.cdx.json` for satisfiable fixtures
5. **Isolation**: Each fixture runs in its own mise sandbox with declared tool versions

## Adding a New SCA Tool Plugin

SCA tools are configured declaratively with mise dependencies and command templates.

### Step 1: Create Plugin File

Create `src/bom_bench/sca_tools/{tool_name}.py`:

```python
"""SCA tool plugin for {TOOL_NAME}."""

import shutil

from bom_bench import hookimpl


@hookimpl
def register_sca_tools() -> dict:
    """Register SCA tool with declarative configuration.

    Returns:
        Dict with tool metadata and declarative config:
        - name: Tool identifier
        - description: Human-readable description
        - supported_ecosystems: List of supported package ecosystems
        - homepage: Tool homepage URL
        - tools: List of mise tool dependencies (e.g., [{"name": "node", "version": "22"}])
        - command: Command template with {output_path} and {project_dir} placeholders
    """
    return {
        "name": "{tool_name}",
        "description": "Description of your tool",
        "supported_ecosystems": ["python", "javascript"],
        "homepage": "https://github.com/org/tool",
        # Mise dependencies (tools needed to run this SCA tool)
        "tools": [
            {"name": "node", "version": "22"},  # Example: if tool needs Node.js
        ],
        # Command template - placeholders will be replaced by sandbox
        "command": "{tool_command} scan {project_dir} -o {output_path}",
    }
```

### Step 2: Add to DEFAULT_PLUGINS

Update `src/bom_bench/plugins/__init__.py`:

```python
DEFAULT_PLUGINS = (
    "bom_bench.fixtures.packse",
    "bom_bench.sca_tools.cdxgen",
    "bom_bench.sca_tools.syft",
    "bom_bench.sca_tools.{tool_name}",  # Add your tool
)
```

### Step 3: Add Tests

Create tests in `tests/unit/test_{tool_name}_plugin.py`.

### SCA Tool Best Practices

1. **Declarative only**: SCA plugins are purely declarative - no execution code needed
2. **Mise dependencies**: Declare all required tools (node, python, etc.) with versions
3. **Placeholders**: Use `{output_path}` and `{project_dir}` in command templates
4. **Sandbox isolation**: Tools run in isolated mise environments with declared dependencies

## Testing Guidelines

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/unit/test_plugins.py -v

# Run with coverage
uv run pytest tests/ --cov=bom_bench --cov-report=html
```

### Writing Tests

- Use fixtures for reusable test data
- Mock external dependencies (subprocess, file I/O)
- Test success and error cases
- Test edge cases (empty inputs, timeouts)

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints for function signatures
- Use dataclasses for data models
- Maximum line length: 100 characters

### Code Quality Tools

```bash
# Format code
ruff format src/bom_bench/

# Lint code
ruff check src/bom_bench/

# Type checking
mypy src/bom_bench/
```

## Pull Request Guidelines

1. Create a feature branch
2. Write tests for new code
3. Update documentation
4. Run tests and linting
5. Create PR with clear description

Thank you for contributing to bom-bench!
