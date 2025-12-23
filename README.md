# bom-bench

Generate package manager manifests and lock files from test scenarios for benchmarking SCA (Software Composition Analysis) tools.

## Overview

**bom-bench** is a modular Python package that generates dependency manifests and lock files for multiple package managers from normalized test scenarios. It's designed to create consistent test datasets for evaluating SCA tool accuracy across different package ecosystems.

**Current Status**: Fully functional for UV package manager with packse scenarios. Architecture supports future expansion to pip, pnpm, Gradle, and custom data sources.

## Features

- ✅ **Multi-Package Manager Architecture**: Plugin-based system ready for UV, pip, pnpm, Gradle
- ✅ **Data Source Abstraction**: Supports packse scenarios (Python), extensible to pnpm-tests, gradle-testkit
- ✅ **Hierarchical Output**: Organized by package manager: `output/{pm}/{scenario}/`
- ✅ **Lock File Generation**: Automated dependency resolution and locking
- ✅ **Groundtruth SBOM Generation**: CycloneDX 1.6 SBOMs for benchmarking SCA tools
- ✅ **Comprehensive CLI**: Multiple entry points, rich filtering options
- ✅ **Fully Tested**: 88 unit and integration tests
- ⏳ **SCA Benchmarking** (Planned): Run Grype, Trivy, Snyk, OSV-Scanner against generated outputs

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
# Generate manifests for default PM (UV)
bom-bench

# Generate with lock files
bom-bench --lock

# Generate for specific scenarios
bom-bench --scenarios fork-basic,local-simple
```

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
python -m bom_bench --lock
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
│   ├── models/             # Data models
│   │   ├── scenario.py     # Scenario dataclasses
│   │   └── result.py       # Result models
│   │
│   └── benchmarking/       # SCA tool integration (stub)
│       ├── runner.py       # Tool execution
│       ├── collectors.py   # Result collection
│       └── reporters.py    # Report generation
│
├── tests/                  # Test suite (88 tests)
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
│
├── data/                  # Data sources (gitignored)
│   └── packse/            # Packse scenarios
│
└── output/                # Generated outputs (gitignored)
    └── uv/                # UV outputs
        └── {scenario}/    # Per-scenario projects
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

### Current (UV)

```
output/
└── uv/
    ├── fork-basic/
    │   ├── pyproject.toml       # Project manifest
    │   ├── uv.lock              # Lock file (with --lock)
    │   ├── uv-lock-output.txt   # Command output log
    │   └── expected.cdx.json    # Expected SBOM (CycloneDX 1.6)
    └── local-simple/
        └── ...
```

**SBOM Generation**: When scenarios include expected package data from packse, bom-bench automatically generates a CycloneDX 1.6 SBOM (`expected.cdx.json`) containing the groundtruth package list. This serves as a reference for benchmarking SCA tool accuracy.

### Future (Multi-PM)

```
output/
├── uv/
│   └── {scenario}/
├── pip/
│   └── {scenario}/
├── pnpm/
│   └── {scenario}/
└── gradle/
    └── {scenario}/
```

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
| CLI | ✅ Complete | All entry points working |
| Tests | ✅ Complete | 71 tests, 100% pass |
| Pip Support | 📝 Stub | Implementation guide provided |
| pnpm Support | 📝 Stub | Implementation guide provided |
| Gradle Support | 📝 Stub | Implementation guide provided |
| SCA Benchmarking | 📝 Stub | Architecture defined |

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
