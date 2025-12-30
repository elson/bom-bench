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

### Development (Using Makefile)

**Quick Reference:**
```bash
make help          # Show all available targets
make install       # Install dependencies and pre-commit hooks
make test          # Run all tests (fast)
make test-cov      # Run tests with coverage report
make coverage-html # Generate HTML coverage report
make lint          # Check code style (no changes)
make format        # Auto-format code with ruff
make typecheck     # Run mypy type checker
make check         # Run all checks (lint + typecheck + test-cov)
make clean         # Remove cache and temporary files
make run           # Run bom-bench (setup + benchmark)
```

**Development Workflow:**
```bash
# Initial setup
make install

# Before committing - format and check everything
make format
make check

# View detailed coverage
make coverage-html
# Opens htmlcov/index.html with line-by-line coverage
```

### Development (Direct Commands)
```bash
# Install dependencies
uv sync

# Run all tests (264 tests)
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/unit/test_package_managers.py -xvs

# Run single test
uv run pytest tests/unit/test_models.py::TestProcessStatus -xvs

# Coverage (current: 87%)
uv run pytest tests/ --cov=src/bom_bench --cov-report=term-missing
uv run pytest tests/ --cov=src/bom_bench --cov-report=html

# Type checking (currently ~24 errors in existing code)
uv run mypy src/

# Linting
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/        # Auto-fix issues
uv run ruff format src/ tests/             # Format code

# Pre-commit hooks (runs on git commit)
uv run pre-commit run --all-files          # Run manually
SKIP=mypy git commit                       # Skip mypy if needed
uv run pre-commit autoupdate              # Update hook versions
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
## Code Quality & Style

### Linting and Formatting
- **Ruff** is the primary linter and formatter (replaces black, isort, flake8, pyupgrade)
- Line length: 100 characters
- Enabled rules: pycodestyle (E), Pyflakes (F), isort (I), pep8-naming (N), pyupgrade (UP), bugbear (B), comprehensions (C4), simplify (SIM)
- Auto-formatting runs on every commit via pre-commit hooks
- Run `make format` before committing to fix issues automatically

### Type Checking
- **Mypy** for static type checking (Python 3.12 target)
- Currently has ~24 type errors in existing code (can be fixed incrementally)
- Type checking runs on `src/` only (tests excluded)
- Use `SKIP=mypy git commit` to bypass if needed
- Ignore missing imports for external packages (pluggy, packse, cyclonedx, tomlkit)

### Pre-commit Hooks
Automatically run on `git commit`:
1. **Ruff linter** - checks and auto-fixes code style
2. **Ruff formatter** - formats code consistently
3. **Mypy** - type checking (warnings only, won't block commits)
4. **Pre-commit hooks** - trailing whitespace, EOF, YAML/TOML/JSON validation, large files, merge conflicts

Skip specific hooks: `SKIP=mypy git commit`

### Code Style
- Avoid comments - code is self-describing
- You don't need to add descriptions of **what** the code is doing (e.g. "loop over the inputs")
- Use comments sparingly to note **why** something is done if the code itself does not make this clear
- Use Python 3.12+ features (use `dict`/`list` instead of `typing.Dict`/`List`)
- Type hints recommended but not strictly enforced

## Testing
- **IMPORTANT:** Use TDD (Test-Driven Development). Write test first, watch it fail, write minimal code to pass
- Run full test suite before committing (`make test` or `uv run pytest tests/ -v`)
- Integration tests require packse server running
- Mock external dependencies in unit tests
- Current coverage: **87%** (264 tests) - run `make coverage` to see report
- **Coverage target: 100%** - All new code must have full test coverage

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

## Development Checklist

### Before Committing
1. Format code: `make format`
2. Run checks: `make check` (lint + typecheck + test with coverage)
3. Verify tests pass: All 264 tests should pass
4. Check coverage: Must be 100% for all new/changed code (87% baseline for existing)

### If You Change Behavior
- Update README.md for user-facing changes
- Update CLAUDE.md for architectural changes
- Update scratchpad.md with decision rationale
- Add tests for new functionality (TDD!)
- Run `make coverage` to ensure coverage doesn't drop

### Coverage Report Interpretation
```bash
# Terminal report with missing lines
make test-cov

# Browse detailed HTML report
make coverage-html
# Open htmlcov/index.html
```

**Coverage target: 100% for all code**
- Current baseline: 87% (264 tests)
- All new code must have 100% coverage
- Existing code should be brought to 100% incrementally
- No PRs should decrease coverage
