# Overview

This is a spike for generating multiple, independent `uv` projects from a set of scenarios provided by `packse`.

# Goal
- This repo contains a script for generating `pyproject.toml` files from scenario TOMLs in `./scenarios/`.
- The generator filters scenarios with `universal = true`, renders the `pyproject.toml` files using a template, and writes outputs to `./output/{SCENARIO_NAME}/`.

# Usage

```bash
uv venv
source .venv/bin/activate
uv run python generate-tomls.py
```

# Requirements
- Target Python 3.12 compatibility
- Update the `generate-tomls.py` file with the script contents
- Make the script runnable with `uv` (https://docs.astral.sh/uv/guides/scripts/#creating-a-python-script)
- Use sensible but minimal dependencies, but if you do require some use the inline script metadata format to declare them (https://packaging.python.org/en/latest/specifications/inline-script-metadata/#inline-script-metadata)
- Only scenarios with the field "universal = true" should be included
- Generated pyproject.toml files should be stored in `./output/{SCENARIO_NAME}` directories
- Use the pyproject.toml format contained in the `./examples/lock.mustache` file
  - **Important!** - the mustache file contains some extra unnecessary output. The pyproject.toml output is in lines 38-61, take this as inspiration and create a separate template file in the project root for final use.