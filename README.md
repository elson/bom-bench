# Overview
Generate and lock multiple `uv` projects from a set of `packse` scenarios.

# Goal
- This repo contains a script for generating `pyproject.toml` files from packse scenario data.
- The generator uses the packse Python API to load scenario data, selects scenarios with `universal: true` (excluding examples), and writes `pyproject.toml` files to `./output/{SCENARIO_NAME}/` directories.
- If `--lock` param is used, attempt `uv lock` on each project and record the results.

# Usage

## Generate pyproject.toml files
```bash
uv run main.py
```

The script will automatically fetch scenarios from the packse repository if the `./scenarios/` directory doesn't exist. The scenarios are loaded programmatically using `packse.inspect.variables_for_templates()`.

## Generate lock files
To also generate `uv.lock` files for each scenario (requires a running packse server at `http://127.0.0.1:3141`):

```bash
uv run main.py --lock
```

This will:
- Run `uv lock --index-url http://127.0.0.1:3141/simple-html` for each generated scenario
- Create a `uv.lock` file (if successful)
- Record command output and exit code in `uv-lock-output.txt` for each scenario
- Display a summary of successes and failures

# Output Format
Each scenario directory (`./output/{SCENARIO_NAME}/`) contains:

## Always generated:
- `pyproject.toml` - Project configuration with:
  - Project name and version (fixed as "project" and "0.1.0")
  - Dependencies from the scenario's root requirements
  - Optional `requires-python` specification
  - Optional `[tool.uv]` section with `required-environments` for universal resolution scenarios

## Generated with `--lock`:
- `uv.lock` - Lock file (if locking succeeded)
- `uv-lock-output.txt` - Command output and exit code

# Implementation Details
- Python 3.12 compatible
- Uses `packse` Python package to fetch and load scenario data programmatically
- Runnable with `uv run`
- Automatically fetches scenarios using `packse.fetch.fetch()` if `./scenarios/` directory doesn't exist
- Loads scenarios using `packse.inspect.variables_for_templates()` with `no_hash=True`
- Dependencies in generated projects use full scenario-prefixed names without hash suffixes for compatibility with `packse serve` (e.g., `wrong-backtracking-basic-a` not `a`)
- Processes only scenarios with `resolver_options.universal: true`
- Excludes scenarios with "example" in the name