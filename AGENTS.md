# Purpose
- Provide concise, actionable guidance to AI coding agents working on this repository.

# Big picture
- See `./README.md` for context.

# Key files and folders
- `./generate-tomls.py` - script file that reads from scenarios.json.
- `./scenarios.json` - JSON file containing packse scenario data, generated from the `./scenarios/` data using `packse inspect --no-hash > scenarios.json`.
- `./scenarios/` - a set of toml files describing various python packaging scenarios, downloaded using the `packse fetch` CLI command. If this doesn't exist, run `packse fetch --dest downloads --force` to recreate it.
- `./output/` - destination for the generated projects.
- `./examples/` - temporary sample files taken from the main `uv` git repository pertaining to generating test data from the scenarios above. These are here to provide example code and context to the AI coding assistant, they will be deleted in the future.

# Available tools
- `uv` Python package manager and build tool
- `packse` - CLI tool for downloading scenario files, viewing details, building the packages, and serving a package index. Run `packse --help` for  usage details.
- 
# Developer workflows
- Use `uv` to manage environments and runs where possible.
- Create or manage a venv with `uv venv`.
- Make scripts runnable via `uv run` by declaring inline script metadata per `README.md` (this will allow `uv` to automatically install the necessary dependencies without needing to specify them on the command line).
- Run commands inside the `uv` environment using `uv run`, for example:

```bash
uv venv
source .venv/bin/activate
uv run python generate-tomls.py
```
# Testing
- Test your work by running the script using `uv run`, checking the output, and iterating towards a solution.

# Project-specific conventions
- Target interpreter: Python 3.12 — keep syntax and stdlib usage compatible.
- Minimal dependencies: prefer stdlib; currently uses only standard `json` module (no external dependencies).
- Output files: `./output/{SCENARIO_NAME}/pyproject.toml`
- Filtering rule: only process scenarios with `resolver_options.universal = true`.
- Dependency naming: use full scenario-prefixed package names from `root.requires[].requirement` field.

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
