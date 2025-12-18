# Purpose
- Provide concise, actionable guidance to AI coding agents working on this repository.

# Big picture
- See `./README.md` for context.

# Key files and folders
- `./main.py` - main entrypoint script that uses the packse Python API to load and process scenarios.
- `./scenarios/` - a set of toml files describing various python packaging scenarios. The script automatically fetches these using `packse.fetch.fetch()` if the directory doesn't exist.
- `./output/` - destination for the generated projects.

# Available tools
- `uv` Python package manager and build tool
- `packse` - Python package and CLI tool. The script uses the Python API (`packse.fetch`, `packse.inspect`) to fetch and load scenarios programmatically.

# Developer workflows
- Use `uv` to manage environments and runs where possible.
- Create or manage a venv with `uv venv`.
- Declare any non-stdlib dependencies in the `pyproject.toml` file
- Run commands inside the `uv` environment using `uv run`, for example:

```bash
# Generate pyproject.toml files
uv run main.py

# Generate pyproject.toml files and lock files (requires packse server running)
uv run main.py --lock
```

# Testing
- Test your work by running the script using `uv run main.py` (and `--lock` if relevant), checking the output, and iterating towards a solution.
- To test lock file generation, ensure packse server is running at http://127.0.0.1:3141 first.

# Project-specific conventions
- Target interpreter: Python 3.12 — keep syntax and stdlib usage compatible.
- Dependencies: Uses `packse` package (declared in `pyproject.toml`).
- Output files:
  - `./output/{SCENARIO_NAME}/pyproject.toml` (always)
  - `./output/{SCENARIO_NAME}/uv.lock` (with --lock)
  - `./output/{SCENARIO_NAME}/uv-lock-output.txt` (with --lock)
- Filtering rules:
  - Only process scenarios with `resolver_options.universal: true`
  - Exclude scenarios with "example" in the name
- Dependency naming: use full scenario-prefixed package names without hash suffixes from `root.requires[].requirement` field (obtained via `packse.inspect.variables_for_templates(..., no_hash=True)`).

# Patterns & examples
- Auto-fetch: Check if `./scenarios/` exists; if not, call `packse.fetch.fetch(dest=scenarios_dir)` to download scenarios.
- Discovery: Use `packse.inspect.find_scenario_files(scenarios_dir)` to discover scenario files, then `packse.inspect.variables_for_templates(scenario_files, no_hash=True)` to load scenario data.
- Iteration: Iterate through `template_vars['scenarios']` array, check `resolver_options.universal`, use `name` field for output directory.
- Dependencies: Extract from `root.requires[].requirement` (e.g., "wrong-backtracking-basic-a==1.0.0").

# Integration points
- `packse` Python API: scenarios are fetched using `packse.fetch.fetch()` and loaded using `packse.inspect` module.
- `uv`: prefer `uv` tooling for venvs, installs, and running scripts; it centralizes environment management.

# What to avoid
- Do not manually read TOML files from `./scenarios/`; always use the packse API (`packse.inspect.variables_for_templates()`).
- Do not process scenarios where `resolver_options.universal != true`.
- Keep external dependencies minimal; currently only `packse` is required.

# If you change behavior
- Update `README.md` to reflect new flags, outputs, runtime requirements and additional usage instructions.
