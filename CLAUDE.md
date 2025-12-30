# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose
Provide concise, actionable guidance to AI coding agents working on this repository.

## Big Picture
bom-bench is a benchmarking tool for SCA (Software Composition Analysis) tools. It uses a **plugin-based architecture** with Pluggy to support multiple package managers and SCA tools. The workflow is:
1. Generate manifests and lock files from test scenarios (setup phase)
2. Run SCA tools against generated projects (benchmark phase)
3. Compare actual vs expected SBOMs using PURL matching

## Project Status
- Early, pre-alpha stage
- Breaking changes are completely acceptable, there are no real users yet
- Do not add backward compatibility code (shims, aliases, switches)

## Project & Context Management
- Create a `.claude/scratchpad.md` doc to document files, edits, decision logs and explorations
- Store official plans in `.claude/plans/` subfolder

## Commands

### Development
```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run all tests (210+ unit tests)
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/unit/test_package_managers.py -xvs

# Run single test
uv run pytest tests/unit/test_models.py::TestProcessStatus -xvs

# Type checking
mypy src/bom_bench/

# Linting/formatting
ruff check src/bom_bench/
ruff format src/bom_bench/
```

### Application Usage
```bash
# Generate test projects (requires packse server at http://127.0.0.1:3141)
uv run bom-bench setup --pm uv

# Run benchmarks
uv run bom-bench benchmark --pm uv --tools cdxgen,syft

# List available tools
uv run bom-bench list-tools --check
```

## Testing
- **IMPORTANT:** Use TDD (Test-Driven Development). Write test first, watch it fail, write minimal code to pass
- Run full test suite before committing (`uv run pytest tests/ -v`)
- Integration tests require packse server running
- Mock external dependencies in unit tests

## Key Architecture

### Plugin System (Pluggy-based)

**Two Plugin Types:**

1. **Package Manager Plugins** (`package_managers/`)
   - **2 hooks only** (simplified from 7 hooks):
     - `register_package_managers()` → Returns dict with `{name, ecosystem, description, supported_sources, installed, version}`
     - `process_scenario(pm_name, scenario, output_dir, timeout)` → Atomic operation that generates manifest, runs lock, creates SBOM
   - Returns dict, framework converts to dataclass
   - Example: `uv.py` for UV package manager

2. **SCA Tool Plugins** (`sca_tools/`)
   - 3 hooks:
     - `register_sca_tools()` → Returns dict with tool info
     - `check_tool_available(tool_name)` → Boolean availability check
     - `scan_project(tool_name, project_dir, output_path, ...)` → Runs tool, returns dict with result
   - Returns dict, framework converts to dataclass
   - Examples: `cdxgen.py`, `syft.py`

**Plugin Registration:** All plugins listed in `plugins/__init__.py::DEFAULT_PLUGINS` tuple.

### Data Flow

```
Scenario (JSON)
  → PM Plugin (process_scenario)
    → Manifest (pyproject.toml)
    → Lock file (uv.lock)
    → Expected SBOM (expected.cdx.json) + meta.json
  → SCA Plugin (scan_project)
    → Actual SBOM (actual.cdx.json)
  → Comparison (PURL matching)
    → Metrics (precision, recall, F1)
```

### Key Models

- `Scenario` - Test scenario with dependencies
- `ProcessScenarioResult` - PM processing result with status (SUCCESS/FAILED/TIMEOUT/UNSATISFIABLE)
- `PMInfo` - PM metadata with `supported_sources` field
- `SCAToolInfo` - SCA tool metadata
- `ScanResult` - SCA tool scan result
- `PurlMetrics` - Benchmark metrics (TP/FP/FN, precision/recall/F1)

## Directory Structure

```
src/bom_bench/
├── cli.py              # CLI entry point using Click
├── config.py           # Constants (paths, defaults)
├── plugins/
│   ├── __init__.py     # DEFAULT_PLUGINS, initialize_plugins()
│   └── hookspecs.py    # Hook specifications (PackageManagerSpec, SCAToolSpec)
├── package_managers/
│   ├── __init__.py     # PM wrapper functions, PMInfo registry
│   └── uv.py          # UV plugin (process_scenario, register_package_managers)
├── sca_tools/
│   ├── __init__.py     # SCA wrapper functions, tool registry
│   ├── cdxgen.py      # CycloneDX generator plugin
│   └── syft.py        # Syft plugin
├── models/
│   ├── scenario.py          # Scenario, Root, Requirement
│   ├── package_manager.py   # PMInfo, ProcessStatus, ProcessScenarioResult
│   ├── sca_tool.py          # SCAToolInfo, ScanResult, PurlMetrics
│   └── result.py            # LockResult, ProcessingResult
├── benchmarking/
│   ├── runner.py       # BenchmarkRunner orchestration
│   ├── comparison.py   # PURL extraction, normalization, comparison
│   └── storage.py      # JSON/CSV persistence
├── generators/sbom/
│   └── cyclonedx.py   # SBOM generation utilities
└── data/
    └── loader.py      # Scenario loading abstraction
```

## Output Structure

### Setup Output (`output/scenarios/{pm}/{scenario}/`)
```
scenarios/
  uv/
    test-scenario/
      ├── expected.cdx.json    # Ground truth SBOM (only if satisfiable)
      ├── meta.json            # {satisfiable, package_manager_result}
      └── assets/
          ├── pyproject.toml   # Generated manifest
          └── uv.lock          # Lock file
```

### Benchmark Output (`output/benchmarks/{tool}/{pm}/`)
```
benchmarks/
  cdxgen/
    uv/
      ├── test-scenario/
      │   ├── actual.cdx.json  # SBOM from SCA tool
      │   └── result.json      # Comparison metrics
      ├── summary.json         # Aggregated stats
      └── results.csv          # All results
```

## Project-Specific Conventions

- **Target**: Python 3.12+
- **Dependencies**: Declared in `pyproject.toml` (packse, pluggy, packageurl-python, tomlkit)
- **Package Manager**: Use `uv` for all operations
- **Filtering**: Only process scenarios with `resolver_options.universal: true`, exclude "example" in name
- **SBOM Format**: CycloneDX 1.6
- **PURL Normalization**:
  - PyPI packages: lowercase, underscores→hyphens
  - Remove qualifiers (version, VCS URLs)

## Plugin Development Patterns

### Adding a Package Manager Plugin

1. Create `package_managers/{pm_name}.py`
2. Implement 2 hooks:
   ```python
   @hookimpl
   def register_package_managers() -> dict:
       return {
           "name": "my-pm",
           "ecosystem": "python",
           "description": "My PM",
           "supported_sources": ["my-source"],
           "installed": shutil.which("my-pm") is not None,
           "version": "1.0.0"
       }

   @hookimpl
   def process_scenario(pm_name, scenario, output_dir, timeout=120) -> Optional[dict]:
       if pm_name != "my-pm":
           return None
       # 1. Generate manifest
       # 2. Run lock command
       # 3. Parse lock, generate SBOM
       # 4. Generate meta.json
       return {
           "pm_name": "my-pm",
           "status": "success",  # or "failed", "timeout", "unsatisfiable"
           "manifest_path": str(path),
           "lock_file_path": str(path),
           "sbom_path": str(path),
           "meta_path": str(path),
           "duration_seconds": 1.5,
           "exit_code": 0
       }
   ```
3. Add to `DEFAULT_PLUGINS` in `plugins/__init__.py`

### Adding an SCA Tool Plugin

1. Create `sca_tools/{tool_name}.py`
2. Implement 3 hooks (see existing plugins for examples)
3. Add to `DEFAULT_PLUGINS`

## Important Implementation Details

### Package Manager Plugin Flow
- 2 hooks total - atomic `process_scenario` combines all operations
- Output directory calculated by framework: `base_dir / "scenarios" / pm_name / scenario_name`
- Scenario compatibility checked via `pm_info.supported_sources` (not a hook)

### SCA Tool Plugin Flow
- Tools run via subprocess against project directory (`assets/` folder)
- Must handle timeouts, missing tools, parse errors
- Return dict, framework converts to `ScanResult`

### Comparison Logic
- Extract PURLs from both expected and actual SBOMs
- Normalize PURLs (lowercase, strip qualifiers)
- Calculate set operations: TP = intersection, FP = actual - expected, FN = expected - actual
- Metrics: precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = harmonic mean

## Common Pitfalls to Avoid

- Don't call removed PM hooks (load_scenarios, validate_scenario, get_output_dir, generate_manifest, run_lock, generate_sbom_for_lock)
- Don't use `data_source` field in PMInfo (use `supported_sources` list instead)
- Don't manually parse TOML files (use packse API for scenarios, tomlkit for generation)
- Don't skip TDD - write test first, watch it fail, then implement
- Don't process non-universal scenarios (`resolver_options.universal: false`)

## If You Change Behavior
- Update README.md for user-facing changes
- Update CLAUDE.md for architectural changes
- Update scratchpad.md with decision rationale
