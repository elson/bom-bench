# Purpose
- Provide concise, actionable guidance to AI coding agents working on this repository.

# Big picture
- See `./README.md` for context.

# Key files and folders
- `./main.py` - main entrypoint, script file that reads from scenarios.json.
- `./scenarios.json` - JSON file containing packse scenario data, generated from the `./scenarios/` data using `packse inspect --no-hash > scenarios.json`.
- `./scenarios/` - a set of toml files describing various python packaging scenarios, downloaded using the `packse fetch` CLI command. If this doesn't exist, run `packse fetch --dest downloads --force` to recreate it.
- `./output/` - destination for the generated projects.

# Available tools
- `uv` Python package manager and build tool
- `packse` - CLI tool for downloading scenario files, viewing details, building the packages, and serving a package index. Run `packse --help` for  usage details.
- 
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
- Minimal dependencies, prefer stdlib.
- Output files:
  - `./output/{SCENARIO_NAME}/pyproject.toml` (always)
  - `./output/{SCENARIO_NAME}/uv.lock` (with --lock)
  - `./output/{SCENARIO_NAME}/uv-lock-output.txt` (with --lock)
- Filtering rules:
  - Only process scenarios with `resolver_options.universal: true`
  - Exclude scenarios with "example" in the name
- Dependency naming: use full scenario-prefixed package names from `root.requires[].requirement` field (which is the default in scenarios.json).

# Patterns & examples
- Discovery: read `scenarios.json`, iterate through `scenarios` array, check `resolver_options.universal`, use `name` field for output directory.
- Dependencies: extract from `root.requires[].requirement` (e.g., "wrong-backtracking-basic-a==1.0.0").

# Integration points
- `packse` CLI: scenarios are fetched with `packse`; using `packse` to inspect or validate scenarios is acceptable.
- `uv`: prefer `uv` tooling for venvs, installs, and running scripts; it centralizes environment management.

# What to avoid
- Do not read from `./scenarios/` TOML files; always use `scenarios.json` as the data source.
- Do not process scenarios where `resolver_options.universal != true`.
- Avoid adding external dependencies; the script currently uses only stdlib and should remain that way unless absolutely necessary.

# If you change behavior
- Update `README.md` to reflect new flags, outputs, runtime requirements and additional usage instructions.
