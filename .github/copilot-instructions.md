# Copilot instructions for packse/uv dataset generator

Purpose
- Provide concise, actionable guidance to AI coding agents working on this repository.

Big picture
- This repo generates `pyproject.toml` files from scenario TOMLs in `downloads/`.
- The generator filters scenarios with `universal = true`, renders the `examples/lock.mustache` template, and writes outputs to `./output/{SCENARIO_NAME}`.

Key files and folders
- `README.md`: requirements, constraints, and goal (Python 3.12, use `uv`).
- `generate-tomls.py`: implement the generator here.
- `examples/lock.mustache`: canonical template for output `pyproject.toml` files.
- `downloads/`: source TOML scenario files.

Developer workflows and `uv` commands
- Use `uv` to manage environments and runs where possible.
- Create or manage a venv with `uv venv`.
- Install runtime tools inside the environment: `uv install packse uv jinja2 toml` (or the minimal set you need).
- Run commands inside the `uv` environment using `uv run`, for example:

```bash
uv venv
uv run python generate-tomls.py
```

- You can still activate the created venv manually if needed: `source .venv/bin/activate`.
- Make `generate-tomls.py` runnable via `uv` by declaring inline script metadata per `README.md` or invoking with `uv run` (this will allow `uv` to automatically install the necessary dependencies without needing to specify them on the command line).

Project-specific conventions
- Target interpreter: Python 3.12 — keep syntax and stdlib usage compatible.
- Minimal dependencies: prefer stdlib; add dependencies only when necessary and declare them via inline script metadata or `pyproject.toml` used by `uv`.
- Output layout: `./output/{SCENARIO_NAME}/pyproject.toml` using the `lock.mustache` structure.
- Filtering rule: only process scenarios with `universal = true`.

Patterns & examples
- Template rendering: populate `examples/lock.mustache` fields from parsed TOML scenario keys.
- Discovery: iterate `downloads/**/*.toml`, parse, check `universal`, and derive `SCENARIO_NAME` from filename or a scenario field.

Integration points
- `packse` CLI: scenarios are fetched with `packse`; using `packse` to inspect or validate scenarios is acceptable.
- `uv`: prefer `uv` tooling for venvs, installs, and running scripts; it centralizes environment management.

What to avoid
- Do not process scenarios missing `universal = true`.
- Avoid heavy dependencies unless needed for reliable template rendering or TOML parsing.

If you change behavior
- Update `README.md` to reflect new flags, outputs, or runtime requirements and document any additional `uv` usage.
