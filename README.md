# bom-bench

Generate package manager manifests and lock files from test scenarios for benchmarking SCA (Software Composition Analysis) tools.

## Overview

**bom-bench** is a modular Python package that generates dependency manifests and lock files for multiple package managers from normalized test scenarios. It's designed to create consistent test datasets for evaluating SCA tool accuracy across different package ecosystems.

**Current Status**: Fully functional for UV package manager with packse scenarios.

## Features

- **Plugin-Based Architecture**: Extensible via Pluggy plugins for package managers and SCA tools
- **Hierarchical Output**: Organized by package manager: `output/{pm}/{scenario}/`
- **Automatic Lock File Generation**: Dependency resolution and locking enabled by default
- **SBOM Generation from Lock Files**: CycloneDX 1.6 SBOMs generated from resolved dependencies
- **Comprehensive CLI**: Multiple entry points, rich filtering options
- **SCA Tool Benchmarking**: Run SCA tools via plugins, compare results with precision/recall metrics
- **Fully Tested**: 230+ unit and integration tests

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/bom-bench
cd bom-bench

# Install with uv
uv pip install -e .

# Or install with pip
pip install -e .
```

### Basic Usage

```bash
# Generate manifests, lock files, and SBOMs for default PM (UV)
bom-bench setup

# Generate for specific scenarios
bom-bench setup --scenarios fork-basic,local-simple
```

### SCA Tool Benchmarking

```bash
# Prerequisites: Install SCA tools
npm install -g @cyclonedx/cdxgen  # cdxgen
brew install syft                  # Syft (macOS)

# Step 1: Generate test projects with expected SBOMs
bom-bench setup --pm uv

# Step 2: List available SCA tools and check installation
bom-bench list-tools --check

# Step 3: Run benchmarking against generated projects
bom-bench benchmark --pm uv --tools cdxgen,syft

# Run with single tool
bom-bench benchmark --pm uv --tools syft

# Run specific scenarios only
bom-bench benchmark --pm uv --tools cdxgen --scenarios fork-basic
```

The benchmark command will:
- Run each SCA tool against generated projects
- Compare actual SBOMs with expected SBOMs using PURL matching
- Calculate precision, recall, and F1 scores
- Save results in JSON and CSV formats

## Architecture

### Directory Structure

```
bom-bench/
├── src/bom_bench/          # Main package (src-layout)
│   ├── cli.py              # CLI orchestration
│   ├── config.py           # Configuration constants
│   │
│   ├── data/               # Data source abstraction
│   │   ├── loader.py       # Scenario loading logic
│   │   └── sources/
│   │       └── packse.py   # Packse implementation
│   │
│   ├── package_managers/   # Package manager plugins
│   │   └── uv.py           # UV implementation (plugin)
│   │
│   ├── sca_tools/          # SCA tool plugins
│   │   ├── cdxgen.py       # cdxgen plugin
│   │   └── syft.py         # Syft plugin
│   │
│   ├── plugins/            # Pluggy-based plugin system
│   │   ├── __init__.py     # Plugin manager + DEFAULT_PLUGINS
│   │   └── hookspecs.py    # Hook specifications
│   │
│   ├── generators/         # Manifest generators
│   │   ├── uv/             # UV generators
│   │   └── sbom/           # SBOM generators
│   │
│   ├── parsers/            # Lock file parsers
│   │   └── uv_lock.py      # UV lock parser
│   │
│   ├── models/             # Data models
│   │   ├── scenario.py     # Scenario dataclasses
│   │   ├── result.py       # Result models
│   │   ├── package_manager.py  # PM models
│   │   └── sca.py          # SCA tool models
│   │
│   └── benchmarking/       # SCA tool benchmarking
│       ├── runner.py       # Benchmark orchestration
│       ├── comparison.py   # SBOM comparison logic
│       └── storage.py      # Result persistence
│
├── tests/                  # Test suite (230+ tests)
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
│
├── data/                  # Data sources (gitignored)
│   └── packse/            # Packse scenarios
│
└── output/                # Generated outputs (gitignored)
    ├── uv/                # Setup outputs
    │   └── {scenario}/    # Per-scenario projects
    └── benchmarks/        # Benchmark outputs
        └── {tool}/{pm}/   # Per-tool, per-PM results
```

### Plugin System

bom-bench uses [Pluggy](https://pluggy.readthedocs.io/) for extensibility. Plugins are organized in `DEFAULT_PLUGINS`:

```python
DEFAULT_PLUGINS = (
    "bom_bench.package_managers.uv",
    "bom_bench.sca_tools.cdxgen",
    "bom_bench.sca_tools.syft",
)
```

## Output Structure

### Setup Output

```
output/
└── scenarios/
    └── uv/
        ├── fork-basic/
        │   ├── expected.cdx.json    # Expected SBOM (pure CycloneDX 1.6)
        │   ├── meta.json            # Metadata (satisfiable, PM result)
        │   └── assets/
        │       ├── pyproject.toml   # Project manifest
        │       └── uv.lock          # Lock file
        └── local-simple/
            └── ...
```

**meta.json structure:**
```json
{
  "satisfiable": true,
  "package_manager_result": {
    "exit_code": 0,
    "stdout": "...",
    "stderr": ""
  }
}
```

### Benchmark Output

```
output/
└── benchmarks/
    └── cdxgen/                  # SCA tool name
        └── uv/                  # Package manager
            ├── fork-basic/
            │   ├── actual.cdx.json   # SBOM from SCA tool
            │   └── result.json       # Comparison metrics
            ├── summary.json          # Aggregated metrics
            └── results.csv           # All results in CSV
```

**Metrics**: Each benchmark result includes:
- **True Positives (TP)**: PURLs in both expected and actual
- **False Positives (FP)**: PURLs in actual but not expected
- **False Negatives (FN)**: PURLs in expected but not actual
- **Precision**: TP / (TP + FP)
- **Recall**: TP / (TP + FN)
- **F1 Score**: Harmonic mean of precision and recall

## Extension Guide

### Adding a New SCA Tool Plugin

1. **Create plugin file**: `src/bom_bench/sca_tools/{tool_name}.py`

2. **Implement the hooks**:

```python
import pluggy
from pathlib import Path
from typing import List, Optional

hookimpl = pluggy.HookimplMarker("bom_bench")

@hookimpl
def register_sca_tools():
    """Register your SCA tool."""
    from bom_bench.models.sca import SCAToolInfo
    return [
        SCAToolInfo(
            name="my-tool",
            description="My SBOM generator",
            supported_ecosystems=["python", "javascript"],
            homepage="https://github.com/example/my-tool"
        )
    ]

@hookimpl
def check_tool_available(tool_name: str) -> Optional[bool]:
    """Check if your tool is installed."""
    if tool_name != "my-tool":
        return None
    import shutil
    return shutil.which("my-tool") is not None

@hookimpl
def generate_sbom(tool_name, project_dir, output_path, ecosystem, timeout=120):
    """Generate SBOM using your tool."""
    if tool_name != "my-tool":
        return None
    # Run tool and return SBOMResult
```

3. **Add to DEFAULT_PLUGINS** in `plugins/__init__.py`

### Adding a New Package Manager Plugin

1. **Create plugin file**: `src/bom_bench/package_managers/{pm_name}.py`

2. **Implement the hooks**:

```python
import pluggy
hookimpl = pluggy.HookimplMarker("bom_bench")

@hookimpl
def register_package_managers():
    from bom_bench.models.package_manager import PMInfo
    return [PMInfo(
        name="my-pm",
        ecosystem="python",
        description="My package manager",
        data_source="my-data-source"
    )]

@hookimpl
def load_scenarios(pm_name, data_dir):
    if pm_name != "my-pm":
        return None
    # Load and return scenarios

@hookimpl
def generate_manifest(pm_name, scenario, output_dir):
    if pm_name != "my-pm":
        return None
    # Generate manifest and return path

@hookimpl
def run_lock(pm_name, project_dir, scenario_name, timeout=120):
    if pm_name != "my-pm":
        return None
    # Run lock command and return LockResult
```

3. **Add to DEFAULT_PLUGINS** in `plugins/__init__.py`

## Development

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run unit tests only
uv run pytest tests/unit/ -v

# Run with coverage
uv run pytest tests/ --cov=bom_bench
```

### Code Quality

```bash
# Type checking
mypy src/bom_bench/

# Linting
ruff check src/bom_bench/

# Formatting
ruff format src/bom_bench/
```

## Requirements

- Python >= 3.12
- UV or pip package manager
- packse >= 0.3.54

### For Lock File Generation
- Running packse server at `http://127.0.0.1:3141` (for UV)

## Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| UV Package Manager | Complete | Fully functional plugin |
| Packse Data Source | Complete | Integrated into UV plugin |
| CLI | Complete | setup, benchmark, list-tools |
| Plugin System | Complete | Pluggy-based with DEFAULT_PLUGINS |
| cdxgen Plugin | Complete | Bundled SCA tool |
| Syft Plugin | Complete | Bundled SCA tool |
| SBOM Comparison | Complete | PURL-based metrics |
| Tests | Complete | 230+ tests |

## License

[Your License Here]

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.
