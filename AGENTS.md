# Purpose
- Provide concise, actionable guidance to AI coding agents working on this repository.

# Big picture
- See `./README.md` for context.

# Key files and folders
- `./generate-tomls.py` - script file.
- `./output/` - destination for the generated projects.
- `./downloads/` - a set of toml files describing various python packaging scenarios, downloaded using the `packse fetch` CLI command. If this doesn't exist, run `packse fetch --dest downloads --force` to recreate it.
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
- Minimal dependencies: prefer stdlib; add dependencies only when necessary and declare them via inline script metadata or `pyproject.toml` used by `uv`.
- Output files: `./output/{SCENARIO_NAME}/pyproject.toml` 
- Filtering rule: only process scenarios with `universal = true`.

# Patterns & examples
- Discovery: iterate `downloads/**/*.toml`, parse, check `universal`, and derive `SCENARIO_NAME` from filename or a scenario field.

# Integration points
- `packse` CLI: scenarios are fetched with `packse`; using `packse` to inspect or validate scenarios is acceptable.
- `uv`: prefer `uv` tooling for venvs, installs, and running scripts; it centralizes environment management.

# What to avoid
- The files in `./downloads` are temporary and will be deleted at a later date. Do not use these files (e.g. `lock.mustache` file) directly in the final script implementation, they are provided as inspiration only. If you need to, create copies of any portions of the files that are useful.
- Do not process scenarios missing `universal = true`.
- Avoid heavy dependencies unless needed for reliable template rendering or TOML parsing.

# If you change behavior
- Update `README.md` to reflect new flags, outputs, runtime requirements and additional usage instructions.
