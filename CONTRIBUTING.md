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
├── cli.py                  # CLI orchestration
├── config.py               # Configuration constants
├── data/                   # Data source utilities
├── package_managers/       # Package manager plugins
├── sca_tools/              # SCA tool plugins
├── plugins/                # Plugin system (hookspecs, DEFAULT_PLUGINS)
├── generators/             # Manifest generators
├── models/                 # Data models
└── benchmarking/           # Benchmarking runner and comparison
```

## Adding a New Package Manager Plugin

Package managers are plugins that load scenarios, generate manifests, and run lock commands.

### Step 1: Create Plugin File

Create `src/bom_bench/package_managers/{pm_name}.py`:

```python
"""Package manager plugin for {PM_NAME}."""

import pluggy
from pathlib import Path
from typing import List, Optional

from bom_bench.models.package_manager import PMInfo
from bom_bench.models.scenario import Scenario
from bom_bench.models.result import LockResult, LockStatus

hookimpl = pluggy.HookimplMarker("bom_bench")


@hookimpl
def register_package_managers() -> List[PMInfo]:
    """Register your package manager."""
    return [
        PMInfo(
            name="{pm_name}",
            ecosystem="{ecosystem}",  # python, javascript, java, etc.
            description="Description of your PM",
            data_source="{data_source_name}"  # 1-to-1 mapping
        )
    ]


@hookimpl
def check_package_manager_available(pm_name: str) -> Optional[bool]:
    """Check if your PM is installed."""
    if pm_name != "{pm_name}":
        return None
    import shutil
    return shutil.which("{pm_command}") is not None


@hookimpl
def load_scenarios(pm_name: str, data_dir: Path) -> Optional[List[Scenario]]:
    """Load scenarios for your PM.

    Args:
        pm_name: Package manager name
        data_dir: Base data directory

    Returns:
        List of scenarios, or None if not handled.
    """
    if pm_name != "{pm_name}":
        return None

    # Fetch data source if needed
    # Parse scenario files
    # Return list of Scenario objects
    return []


@hookimpl
def generate_manifest(
    pm_name: str,
    scenario: Scenario,
    output_dir: Path
) -> Optional[Path]:
    """Generate manifest file.

    Args:
        pm_name: Package manager name
        scenario: Scenario to generate manifest for
        output_dir: Output directory

    Returns:
        Path to manifest file, or None if not handled.
    """
    if pm_name != "{pm_name}":
        return None

    # Extract dependencies from scenario.root.requires
    # Generate manifest content
    # Write to output_dir
    # Return path to manifest
    return None


@hookimpl
def run_lock(
    pm_name: str,
    project_dir: Path,
    scenario_name: str,
    timeout: int = 120
) -> Optional[LockResult]:
    """Run lock command.

    Args:
        pm_name: Package manager name
        project_dir: Directory containing manifest
        scenario_name: Scenario name for logging
        timeout: Timeout in seconds

    Returns:
        LockResult, or None if not handled.
    """
    if pm_name != "{pm_name}":
        return None

    # Run lock command (e.g., npm install --lockfile-only)
    # Return LockResult with status
    return None
```

### Step 2: Add to DEFAULT_PLUGINS

Update `src/bom_bench/plugins/__init__.py`:

```python
DEFAULT_PLUGINS = (
    "bom_bench.package_managers.uv",
    "bom_bench.package_managers.{pm_name}",  # Add your PM
    "bom_bench.sca_tools.cdxgen",
    "bom_bench.sca_tools.syft",
)
```

### Step 3: Add Tests

Create tests in `tests/unit/test_{pm_name}_plugin.py`.

## Adding a New SCA Tool Plugin

SCA tools generate SBOMs from project files.

### Step 1: Create Plugin File

Create `src/bom_bench/sca_tools/{tool_name}.py`:

```python
"""SCA tool plugin for {TOOL_NAME}."""

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional

import pluggy

from bom_bench.models.sca import SCAToolInfo, SBOMResult, SBOMGenerationStatus

hookimpl = pluggy.HookimplMarker("bom_bench")


def _get_version() -> Optional[str]:
    """Get tool version if installed."""
    try:
        result = subprocess.run(
            ["{tool_command}", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


@hookimpl
def register_sca_tools() -> List[SCAToolInfo]:
    """Register your SCA tool."""
    return [
        SCAToolInfo(
            name="{tool_name}",
            version=_get_version(),
            description="Description of your tool",
            supported_ecosystems=["python", "javascript"],
            homepage="https://github.com/org/tool"
        )
    ]


@hookimpl
def check_tool_available(tool_name: str) -> Optional[bool]:
    """Check if your tool is installed."""
    if tool_name != "{tool_name}":
        return None
    return shutil.which("{tool_command}") is not None


@hookimpl
def generate_sbom(
    tool_name: str,
    project_dir: Path,
    output_path: Path,
    ecosystem: str,
    timeout: int = 120
) -> Optional[SBOMResult]:
    """Generate SBOM using your tool.

    Args:
        tool_name: Tool name to check
        project_dir: Directory to scan
        output_path: Where to write SBOM
        ecosystem: Package ecosystem
        timeout: Timeout in seconds

    Returns:
        SBOMResult, or None if not handled.
    """
    if tool_name != "{tool_name}":
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    try:
        cmd = ["{tool_command}", str(project_dir), "-o", str(output_path)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration = time.time() - start_time

        if result.returncode == 0 and output_path.exists():
            # Validate JSON
            with open(output_path) as f:
                json.load(f)
            return SBOMResult.success(
                tool_name="{tool_name}",
                sbom_path=output_path,
                duration_seconds=duration
            )
        else:
            return SBOMResult.failed(
                tool_name="{tool_name}",
                error_message=result.stderr or f"Exit code: {result.returncode}",
                duration_seconds=duration
            )

    except subprocess.TimeoutExpired:
        return SBOMResult.failed(
            tool_name="{tool_name}",
            error_message=f"Timeout after {timeout}s",
            status=SBOMGenerationStatus.TIMEOUT
        )
    except FileNotFoundError:
        return SBOMResult.failed(
            tool_name="{tool_name}",
            error_message="Tool not found in PATH",
            status=SBOMGenerationStatus.TOOL_NOT_FOUND
        )
```

### Step 2: Add to DEFAULT_PLUGINS

Update `src/bom_bench/plugins/__init__.py`:

```python
DEFAULT_PLUGINS = (
    "bom_bench.package_managers.uv",
    "bom_bench.sca_tools.cdxgen",
    "bom_bench.sca_tools.syft",
    "bom_bench.sca_tools.{tool_name}",  # Add your tool
)
```

### Step 3: Add Tests

Create tests in `tests/unit/test_{tool_name}_plugin.py`.

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
