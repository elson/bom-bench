# Overview

Generate and lock multiple `uv` projects from a set of scenarios provided by `packse`.

# Goal
- This repo contains a script for generating `pyproject.toml` files from packse scenario data.
- The generator reads scenario data from `./scenarios.json`, filters scenarios with `universal = true` (excluding examples), and writes `pyproject.toml` files to `./output/{SCENARIO_NAME}/` directories.
- If `--lock` param is used, attempt `uv lock` on each project and record the results.

# Usage

## Generate pyproject.toml files

```bash
uv run generate-tomls.py
```

The script requires `scenarios.json` to be present in the current directory. If the file is not found, you can fetch scenarios using packse.

## Generate lock files

To also generate `uv.lock` files for each scenario (requires a running packse server at `http://127.0.0.1:3141`):

```bash
uv run generate-tomls.py --lock
```

This will:
- Run `uv lock --index-url http://127.0.0.1:3141/simple-html` for each generated scenario
- Create a `uv.lock` file (if successful)
- Record command output and exit code in `uv-lock-output.txt` for each scenario
- Display a summary of successes and failures

# Output Format

Each scenario directory (`./output/{SCENARIO_NAME}/`) contains:

**Always generated:**
- `pyproject.toml` - Project configuration with:
  - Project name and version (fixed as "project" and "0.1.0")
  - Dependencies from the scenario's root requirements
  - Optional `requires-python` specification
  - Optional `[tool.uv]` section with `required-environments` for universal resolution scenarios

**Generated with --lock:**
- `uv.lock` - Lock file (if locking succeeded)
- `uv-lock-output.txt` - Command output and exit code

# Implementation Details
- Python 3.12 compatible
- No external dependencies required
- Runnable with `uv run` via inline script metadata
- Dependencies use full scenario-prefixed names for compatibility with `packse serve` (e.g., `wrong-backtracking-basic-a` not `a`)
- Processes only scenarios with `resolver_options.universal: true`
- Excludes scenarios with "example" in the name