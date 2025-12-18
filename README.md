# Overview

This is a spike for generating multiple, independent `uv` projects from a set of scenarios provided by `packse`.

# Goal
- This repo contains a script for generating `pyproject.toml` files from packse scenario data.
- The generator reads scenario data from `./scenarios.json`, filters scenarios with `universal = true` (excluding any with "example" in the name), and writes `pyproject.toml` files to `./output/{SCENARIO_NAME}/` directories.

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
  - Dependencies from the scenario's root requirements (with full scenario-prefixed package names)
  - Optional `requires-python` specification
  - Optional `[tool.uv]` section with `required-environments` for universal resolution scenarios

**Generated with --lock:**
- `uv.lock` - Lock file (if locking succeeded)
- `uv-lock-output.txt` - Command output and exit code

# Implementation Details
- Python 3.12 compatible
- No external dependencies required (uses standard library `json` module)
- Runnable with `uv run` via inline script metadata
- Dependencies use full scenario-prefixed names (e.g., `wrong-backtracking-basic-a` not just `a`)
- Processes only scenarios with `resolver_options.universal = true`
- Excludes scenarios with "example" in the name