# Overview

This is a spike for generating multiple, independent `uv` projects from a set of scenarios provided by `packse`.

# Goal
- This repo contains a script for generating `pyproject.toml` files from packse scenario data.
- The generator reads scenario data from `./scenarios.json`, filters scenarios with `universal = true`, and writes `pyproject.toml` files to `./output/{SCENARIO_NAME}/` directories.

# Usage

```bash
uv run generate-tomls.py
```

The script requires `scenarios.json` to be present in the current directory. If the file is not found, you can fetch scenarios using packse.

# Output Format

Each generated `pyproject.toml` includes:
- Project name and version (fixed as "project" and "0.1.0")
- Dependencies from the scenario's root requirements (with full scenario-prefixed package names)
- Optional `requires-python` specification
- Optional `[tool.uv]` section with `required-environments` for universal resolution scenarios

# Implementation Details
- Python 3.12 compatible
- No external dependencies required (uses standard library `json` module)
- Runnable with `uv run` via inline script metadata
- Dependencies use full scenario-prefixed names (e.g., `wrong-backtracking-basic-a` not just `a`)
- Processes only scenarios with `resolver_options.universal = true`