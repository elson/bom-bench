# bom-bench

Generate package manager manifests and lock files from test scenarios for benchmarking SCA (Software Composition Analysis) tools.

## Overview

**bom-bench** is a modular Python package that generates dependency manifests and lock files for multiple package managers from normalized test scenarios. It's designed to create consistent test datasets for evaluating SCA tool accuracy across different package ecosystems.

**Current Status**: Fully functional for UV package manager with packse scenarios. Architecture supports future expansion to pip, pnpm, Gradle, and custom data sources.

## Features

- ✅ **Multi-Package Manager Architecture**: Plugin-based system ready for UV, pip, pnpm, Gradle
- ✅ **Data Source Abstraction**: Supports packse scenarios (Python), extensible to pnpm-tests, gradle-testkit
- ✅ **Hierarchical Output**: Organized by package manager: `output/{pm}/{scenario}/`
- ✅ **Automatic Lock File Generation**: Dependency resolution and locking enabled by default
- ✅ **SBOM Generation from Lock Files**: CycloneDX 1.6 SBOMs generated from resolved dependencies
- ✅ **Comprehensive CLI**: Multiple entry points, rich filtering options
- ✅ **Plugin-Based SCA Benchmarking**: Run SCA tools via Pluggy plugins, compare results
- ✅ **Fully Tested**: 230+ unit and integration tests

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

### Advanced Usage

```bash
# Generate for multiple package managers (when implemented)
bom-bench --package-managers uv,pip

# Generate for all available package managers
bom-bench --package-managers all

# Custom output directory
bom-bench --output-dir /path/to/output

# Include non-universal scenarios
bom-bench --no-universal-filter

# Module entry point
python -m bom_bench
```

## Architecture

### Directory Structure

```
bom-bench/
├── src/bom_bench/          # Main package (src-layout)
│   ├── cli.py              # CLI orchestration
│   ├── config.py           # Configuration constants
│   │
│   ├── data/               # Data source abstraction
│   │   ├── base.py         # DataSource ABC
│   │   ├── loader.py       # Scenario loading logic
│   │   └── sources/
│   │       ├── packse.py   # Packse implementation ✅
│   │       ├── pnpm_tests.py      # pnpm tests (stub)
│   │       └── gradle_testkit.py  # Gradle tests (stub)
│   │
│   ├── package_managers/   # Package manager plugins
│   │   ├── base.py         # PackageManager ABC
│   │   ├── uv.py           # UV implementation ✅
│   │   ├── pip.py          # Pip (stub)
│   │   ├── pnpm.py         # pnpm (stub)
│   │   └── gradle.py       # Gradle (stub)
│   │
│   ├── generators/         # Manifest generators
│   │   ├── uv/             # UV generators ✅
│   │   ├── sbom/           # SBOM generators ✅
│   │   ├── pnpm/           # pnpm generators (stub)
│   │   └── gradle/         # Gradle generators (stub)
│   │
│   ├── parsers/            # Lock file parsers
│   │   └── uv_lock.py      # UV lock parser ✅
│   │
│   ├── models/             # Data models
│   │   ├── scenario.py     # Scenario dataclasses
│   │   ├── result.py       # Result models
│   │   └── sca.py          # SCA tool models ✅
│   │
│   ├── plugins/            # Pluggy-based plugin system ✅
│   │   ├── __init__.py     # Plugin manager
│   │   ├── hookspecs.py    # Hook specifications
│   │   └── bundled/        # Bundled plugins
│   │       ├── cdxgen.py   # cdxgen plugin ✅
│   │       └── syft.py     # Syft plugin ✅
│   │
│   └── benchmarking/       # SCA tool benchmarking ✅
│       ├── runner.py       # Benchmark orchestration
│       ├── comparison.py   # SBOM comparison logic
│       └── storage.py      # Result persistence
│
├── tests/                  # Test suite (170+ tests)
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

### Key Components

#### 1. Data Sources
**Purpose**: Fetch and normalize test scenarios from various sources.

- **Packse** (✅ Implemented): Python packaging scenarios
- **pnpm-tests** (Stub): pnpm test fixtures
- **gradle-testkit** (Stub): Gradle dependency tests

#### 2. Package Managers
**Purpose**: Generate manifests and lock files for different package ecosystems.

- **UV** (✅ Implemented): Fast Python package manager
- **Pip** (Stub): Traditional Python package manager
- **pnpm** (Stub): Fast Node.js package manager
- **Gradle** (Stub): Java/Kotlin build tool

#### 3. CLI
**Purpose**: Orchestrate scenario loading, manifest generation, and locking.

Two entry points:
- `bom-bench` - Installed command
- `python -m bom_bench` - Module entry

## Output Structure

### Setup Output

```
output/
└── uv/
    ├── fork-basic/
    │   ├── pyproject.toml       # Project manifest
    │   ├── uv.lock              # Lock file (always generated)
    │   ├── uv-lock-output.txt   # Command output log
    │   └── expected.cdx.json    # Expected SBOM (CycloneDX 1.6)
    └── local-simple/
        └── ...
```

**SBOM Generation**: After successful dependency resolution, bom-bench automatically generates a CycloneDX 1.6 SBOM (`expected.cdx.json`) from the lock file. This SBOM contains all resolved packages and serves as a reference for benchmarking SCA tool accuracy.

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

### Adding a New Package Manager

1. **Create implementation file**: `src/bom_bench/package_managers/{pm_name}.py`
2. **Inherit from `PackageManager` ABC**
3. **Implement required methods**:
   - `generate_manifest()` - Generate manifest file
   - `run_lock()` - Execute lock command
   - `validate_scenario()` - Check compatibility
4. **Create generator** (if needed): `src/bom_bench/generators/{pm_name}/`
5. **Register in `__init__.py`**: Add to `PACKAGE_MANAGERS` dict
6. **Add tests**: `tests/unit/test_package_managers.py`

See `src/bom_bench/package_managers/pip.py` (stub) for detailed implementation guide.

### Adding a New Data Source

1. **Create implementation file**: `src/bom_bench/data/sources/{source_name}.py`
2. **Inherit from `DataSource` ABC**
3. **Implement required methods**:
   - `fetch()` - Download/clone source data
   - `load_scenarios()` - Parse and normalize scenarios
   - `needs_fetch()` - Check if fetch needed
4. **Set `supported_pms`**: Declare compatible package managers
5. **Register in `__init__.py`**: Add to `DATA_SOURCES` dict
6. **Update config**: Add to `DATA_SOURCE_PM_MAPPING`
7. **Add tests**: `tests/unit/test_data_sources.py`

See `src/bom_bench/data/sources/pnpm_tests.py` (stub) for detailed implementation guide.

### Adding a New SCA Tool Plugin

bom-bench uses [Pluggy](https://pluggy.readthedocs.io/) for SCA tool plugins. Plugins can be:
- **Bundled**: Shipped with bom-bench (e.g., cdxgen)
- **External**: Installed via pip (e.g., `pip install bom-bench-syft`)

#### Creating an External Plugin

1. **Create a new Python package** (e.g., `bom-bench-syft`)

2. **Implement the hooks**:

```python
# bom_bench_syft/plugin.py
import pluggy
from pathlib import Path
from typing import List, Optional

hookimpl = pluggy.HookimplMarker("bom_bench")

@hookimpl
def bom_bench_register_sca_tools():
    """Register your SCA tool."""
    from bom_bench.models.sca import SCAToolInfo
    return [
        SCAToolInfo(
            name="syft",
            description="Anchore Syft SBOM generator",
            supported_ecosystems=["python", "javascript", "go"],
            homepage="https://github.com/anchore/syft"
        )
    ]

@hookimpl
def bom_bench_check_tool_available(tool_name: str) -> Optional[bool]:
    """Check if your tool is installed."""
    if tool_name != "syft":
        return None
    import shutil
    return shutil.which("syft") is not None

@hookimpl
def bom_bench_generate_sbom(tool_name, project_dir, output_path, ecosystem, timeout=120):
    """Generate SBOM using your tool."""
    if tool_name != "syft":
        return None

    from bom_bench.models.sca import SBOMResult, SBOMGenerationStatus
    import subprocess
    import time

    start = time.time()
    try:
        result = subprocess.run(
            ["syft", str(project_dir), "-o", "cyclonedx-json", "--file", str(output_path)],
            capture_output=True, text=True, timeout=timeout
        )
        duration = time.time() - start

        if result.returncode == 0:
            return SBOMResult.success("syft", output_path, duration)
        return SBOMResult.failed("syft", result.stderr, duration_seconds=duration)
    except subprocess.TimeoutExpired:
        return SBOMResult.failed("syft", f"Timeout after {timeout}s",
                                  status=SBOMGenerationStatus.TIMEOUT)
```

3. **Register via entry point** in `pyproject.toml`:

```toml
[project.entry-points."bom_bench"]
syft = "bom_bench_syft.plugin"
```

4. **Install and use**:

```bash
pip install bom-bench-syft
bom-bench list-tools --check  # Should show syft
bom-bench benchmark --tools syft
```

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

- Python ≥3.12
- UV or pip package manager
- packse ≥0.3.54

### For Lock File Generation
- Running packse server at `http://127.0.0.1:3141` (for UV/pip)
- Or appropriate registry/repository for other package managers

## Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| UV Package Manager | ✅ Complete | Fully functional |
| Packse Data Source | ✅ Complete | Fully functional |
| CLI | ✅ Complete | setup, benchmark, list-tools |
| Plugin System | ✅ Complete | Pluggy-based SCA tool plugins |
| cdxgen Plugin | ✅ Complete | Bundled, fully functional |
| Syft Plugin | ✅ Complete | Bundled, fully functional |
| SBOM Comparison | ✅ Complete | PURL-based metrics |
| Tests | ✅ Complete | 230+ tests, 100% pass |
| Pip Support | 📝 Stub | Implementation guide provided |
| pnpm Support | 📝 Stub | Implementation guide provided |
| Gradle Support | 📝 Stub | Implementation guide provided |

## Documentation

- **README.md** (this file) - Overview and quick start
- **VALIDATION.md** - Refactoring validation report
- **AGENTS.md** - Module descriptions and architecture
- **CONTRIBUTING.md** - Extension and development guide

## License

[Your License Here]

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Adding new package managers
- Adding new data sources
- Implementing SCA tool integrations
- Running tests and code quality checks
