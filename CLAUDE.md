# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose
Provide concise, actionable guidance to AI coding agents working on this repository.

## Big Picture
bom-bench is a benchmarking tool for SCA (Software Composition Analysis) tools. It uses a **fixture-based architecture** with:
- **Fixture Sets**: Pre-generated test projects with expected SBOMs (provided by plugins like packse)
- **SCA Tool Plugins**: Declarative configs for running SCA tools (cdxgen, syft)
- **Mise Sandboxes**: Isolated execution environments with tool versioning

The workflow is:
1. Load fixtures from plugins (manifest, lock file, expected SBOM)
2. Run SCA tools in isolated sandboxes via mise
3. Compare actual vs expected SBOMs using PURL matching

## Project Status
- Early, pre-alpha stage
- Breaking changes are completely acceptable, there are no real users yet
- Do not add backward compatibility code (shims, aliases, switches)

## Project & Context Management
- Create a `.claude/scratchpad.md` doc to document files, edits, decision logs, exploration notes, etc. Update this file regularly as you work.
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
make typecheck     # Run pyright type checker
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

# Run all tests (231 tests)
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/unit/test_fixture_models.py -xvs

# Run single test
uv run pytest tests/unit/test_sandbox.py::TestSandbox -xvs

# Coverage
uv run pytest tests/ --cov=src/bom_bench --cov-report=term-missing
uv run pytest tests/ --cov=src/bom_bench --cov-report=html

# Type checking
uv run pyright src/

# Linting
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/        # Auto-fix issues
uv run ruff format src/ tests/             # Format code

# Pre-commit hooks (runs on git commit)
uv run pre-commit run --all-files          # Run manually
SKIP=pyright git commit                    # Skip pyright if needed
uv run pre-commit autoupdate              # Update hook versions
```

### Application Usage
```bash
# Run benchmarks against all fixture sets with all available tools
uv run bom-bench benchmark

# Run benchmarks with specific tools and fixture sets
uv run bom-bench benchmark --tools cdxgen,syft --fixture-sets packse

# Run specific fixtures only
uv run bom-bench benchmark --fixtures fork-basic,fork-marker-selection

# List available fixture sets
uv run bom-bench list-fixtures

# List available SCA tools (with installation status)
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
- **Pyright/Pylance** for static type checking (Python 3.12 target)
- Pyright is the CLI tool, Pylance is the VS Code integration
- Type checking runs on `src/` only (tests excluded)
- Use `SKIP=pyright git commit` to bypass if needed
- Basic type checking mode with missing imports ignored for external packages

### Pre-commit Hooks
Automatically run on `git commit`:
1. **Ruff linter** - checks and auto-fixes code style
2. **Ruff formatter** - formats code consistently
3. **Pyright** - type checking (warnings only, won't block commits)
4. **Pre-commit hooks** - trailing whitespace, EOF, YAML/TOML/JSON validation, large files, merge conflicts

Skip specific hooks: `SKIP=pyright git commit`

### Code Style
- Avoid comments - code is self-describing
- You don't need to add descriptions of **what** the code is doing (e.g. "loop over the inputs")
- Use comments sparingly to note **why** something is done if the code itself does not make this clear
- Use Python 3.12+ features (use `dict`/`list` instead of `typing.Dict`/`List`)
- Type hints recommended but not strictly enforced

### YAGNI principle (you ain't gonna need it!)
- Avoid adding speculative features or code to support future secnarios unless explicitly instructed to do so by the user
- Avoid adding stubs or similar placeholders, unless instructed to do so
- Ask for permission if you really think it's a good idea in a specific situation

## Testing
- **IMPORTANT:** Use TDD (Test-Driven Development). Write test first, watch it fail, write minimal code to pass
- Run full test suite before committing (`make test` or `uv run pytest tests/ -v`)
- Mock external dependencies in unit tests (subprocess, file I/O)
- Current tests: **231 tests** - run `make test` to verify
- **Coverage target: 100%** - All new code must have full test coverage

## Key Architecture

### Plugin System (Pluggy-based)

**Two Plugin Types:**

1. **Fixture Set Plugins** (`fixtures/`)
   - Single hook: `register_fixture_sets(bom_bench)` → Returns list of fixture set dicts
   - Each fixture set contains: name, ecosystem, environment config (mise tools), and fixtures
   - Example: `packse.py` provides Python dependency resolution test scenarios

2. **SCA Tool Plugins** (`sca_tools/`)
   - 2 hooks:
     - `register_sca_tools()` → Returns dict with tool info and declarative config
     - `scan_project(tool_name, project_dir, output_path, ...)` → Runs tool, returns dict with result
   - Examples: `cdxgen.py`, `syft.py`

**Plugin Registration:** All plugins listed in `plugins/__init__.py::DEFAULT_PLUGINS` tuple.

### Data Flow

```
FixtureSet Plugin
  → Fixtures (manifest, lock, expected SBOM)
    │
    v
Sandbox (mise-based isolation)
  → SCA Tool via `mise run sca`
    → Actual SBOM (actual.cdx.json)
      │
      v
Comparison (PURL matching)
  → Metrics (precision, recall, F1)
```

### Key Models

- `FixtureSet` - Collection of fixtures with shared environment config
- `Fixture` - Single test case with files (manifest, lock, expected SBOM)
- `FixtureSetEnvironment` - Mise tools and env vars for fixture set
- `SCAToolInfo` - SCA tool metadata (name, version, ecosystems)
- `SCAToolConfig` - Declarative tool config (mise tools, command template)
- `ScanResult` - SCA tool scan result with status
- `PurlMetrics` - Benchmark metrics (TP/FP/FN, precision/recall/F1)
- `Sandbox` - Context manager for isolated execution

## Directory Structure

```
src/bom_bench/
├── cli.py              # CLI: benchmark, list-fixtures, list-tools
├── config.py           # Constants (paths, defaults)
├── logging.py          # Logging configuration
├── plugins/
│   ├── __init__.py     # DEFAULT_PLUGINS, initialize_plugins()
│   └── hookspecs.py    # Hook specifications (FixtureSetSpec, SCAToolSpec)
├── fixtures/
│   ├── __init__.py     # Fixture loading utilities
│   ├── loader.py       # FixtureSetLoader with caching
│   └── packse.py       # Packse fixture set plugin
├── sca_tools/
│   ├── __init__.py     # SCA wrapper functions, tool registry
│   ├── cdxgen.py       # CycloneDX generator plugin
│   └── syft.py         # Syft plugin
├── models/
│   ├── fixture.py      # FixtureSet, Fixture, FixtureFiles
│   ├── sandbox.py      # SandboxConfig, SandboxResult
│   ├── sca_tool.py     # SCAToolInfo, SCAToolConfig, ScanResult, PurlMetrics
│   └── scenario.py     # Scenario models (for packse integration)
├── sandbox/
│   ├── mise.py         # ToolSpec, generate_mise_toml(), MiseRunner
│   └── sandbox.py      # Sandbox context manager
├── runner/
│   ├── runner.py       # BenchmarkRunner orchestration
│   └── executor.py     # Single fixture+tool execution
├── benchmarking/
│   └── comparison.py   # PURL extraction, normalization, comparison
└── generators/sbom/
    └── cyclonedx.py    # SBOM generation utilities
```

## Output Structure

### Benchmark Output (`output/benchmarks/{tool}/{fixture_set}/`)
```
benchmarks/
  cdxgen/
    packse/
      ├── fork-basic/
      │   ├── actual.cdx.json  # SBOM from SCA tool
      │   └── result.json      # Comparison metrics
      ├── summary.json         # Aggregated stats per tool+fixture_set
      └── results.csv          # All results
  syft/
    packse/
      └── ...
```

### Fixture Cache (`data/fixture_sets/{set_name}/`)
```
data/fixture_sets/
  packse/
    ├── .cache_manifest.json   # Hash for cache invalidation
    ├── fork-basic/
    │   ├── pyproject.toml     # Manifest
    │   ├── uv.lock            # Lock file
    │   ├── expected.cdx.json  # Ground truth SBOM
    │   └── meta.json          # {satisfiable: true/false}
    └── ...
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

### Adding a Fixture Set Plugin

1. Create `fixtures/{source_name}.py`
2. Implement the hook with dependency injection:
   ```python
   from bom_bench import hookimpl

   @hookimpl
   def register_fixture_sets(bom_bench) -> list[dict]:
       return [{
           "name": "my-fixtures",
           "description": "My test fixtures",
           "ecosystem": "python",
           "environment": {
               "tools": [
                   {"name": "uv", "version": "0.5.11"},
                   {"name": "python", "version": "3.12"},
               ],
               "env_vars": {"UV_INDEX_URL": "http://localhost:3141"},
               "registry_url": "http://localhost:3141",
           },
           "fixtures": [
               {
                   "name": "test-case-1",
                   "files": {
                       "manifest": "/path/to/pyproject.toml",
                       "lock_file": "/path/to/uv.lock",
                       "expected_sbom": "/path/to/expected.cdx.json",
                       "meta": "/path/to/meta.json",
                   },
                   "satisfiable": True,
               }
           ],
       }]
   ```
3. Add to `DEFAULT_PLUGINS` in `plugins/__init__.py`

### Adding an SCA Tool Plugin

1. Create `sca_tools/{tool_name}.py`
2. Implement 2 hooks:
   ```python
   from bom_bench import hookimpl

   @hookimpl
   def register_sca_tools() -> dict:
       return {
           "name": "my-tool",
           "version": "1.0.0",
           "description": "My SCA tool",
           "supported_ecosystems": ["python"],
           "installed": shutil.which("my-tool") is not None,
           "tools": [{"name": "node", "version": "22"}],  # mise deps
           "command": "my-tool scan -o {output_path} {project_dir}",
       }

   @hookimpl
   def scan_project(tool_name, project_dir, output_path, timeout=120) -> dict | None:
       if tool_name != "my-tool":
           return None
       # Run tool subprocess
       return {
           "tool_name": "my-tool",
           "status": "success",
           "sbom_path": str(output_path),
           "duration_seconds": 1.5,
           "exit_code": 0,
       }
   ```
3. Add to `DEFAULT_PLUGINS`

## Important Implementation Details

### Sandbox Execution Flow
- Each benchmark creates an isolated temp directory
- `mise.toml` generated with fixture env + SCA tool env combined
- Files copied from fixture cache to sandbox
- SCA tool runs via `mise run sca` for tool version isolation
- Sandbox cleaned up automatically (context manager pattern)

### SCA Tool Plugin Flow
- Tools declare their mise dependencies (e.g., node for cdxgen)
- Command template uses `{output_path}` and `{project_dir}` placeholders
- Must handle timeouts, missing tools, parse errors
- Return dict, framework converts to `ScanResult`

### Comparison Logic
- Extract PURLs from both expected and actual SBOMs
- Normalize PURLs (lowercase, strip qualifiers)
- Calculate set operations: TP = intersection, FP = actual - expected, FN = expected - actual
- Metrics: precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = harmonic mean

## Common Pitfalls to Avoid

- Package Manager plugins no longer exist - use Fixture Set plugins instead
- Don't run SCA tools directly - use the Sandbox context manager for isolation
- Don't manually generate mise.toml - use `generate_mise_toml()` helper
- Don't skip TDD - write test first, watch it fail, then implement
- Fixture sets handle their own environment - don't hardcode tool versions

## Development Checklist

### Before Committing
1. Format code: `make format`
2. Run checks: `make check` (lint + typecheck + test with coverage)
3. Verify tests pass: All 231 tests should pass
4. Check coverage: Must be 100% for all new/changed code

### If You Change Behavior
- Update README.md for user-facing changes
- Update CLAUDE.md for architectural changes
- Update scratchpad.md with decision rationale
- Add tests for new functionality (TDD!)
- Run `make test-cov` to ensure coverage doesn't drop

### Coverage Report Interpretation
```bash
# Terminal report with missing lines
make test-cov

# Browse detailed HTML report
make coverage-html
# Open htmlcov/index.html
```

**Coverage target: 100% for all code**
- All new code must have 100% coverage
- Existing code should be brought to 100% incrementally
- No PRs should decrease coverage
