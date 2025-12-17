# Overview

This is a spike for generating a data set of `uv` projects from a set of scenarios provided by `packse`.

## Assets

- `generate-tomls.py` - placeholder script file
- `downloads/` - folder containing a set of toml files describing various python packaging scenarios, downloaded using the `packse fetch` CLI command.
  - If this doesn't exist, run `packse fetch --dest downloads --force` to recreate it.
- `examples/` - contains sample files taken from the main `uv` git repository pertaining to generating test data from the scenarios above. These are here to provide example code and context to the AI coding assistant.

## Available tools

- `uv` Python package manager and build tool
- `packse` - CLI tool for downloading scenario files, viewing details, building the packages, and serving a package index. Run `packse --help` for more usage details.

## Goal

Create a simple Python script to generate valid `pyproject.toml` files for the scenarios contained within the `downloads/` folder.

## Requirements

- Target Python 3.12 compatibility
- Update the `generate-tomls.py` file with the script contents
- Make the script runnable with `uv` (https://docs.astral.sh/uv/guides/scripts/#creating-a-python-script)
- Use sensible but minimal dependencies, but if you do require some use the inline script metadata format to declare them (https://packaging.python.org/en/latest/specifications/inline-script-metadata/#inline-script-metadata)
- Only scenarios with the field "universal = true" should be included
- Generated pyproject.toml files should be stored in `./output/{SCENARIO_NAME}` directories
- Use the pyproject.toml format contained in the `./examples/lock.mustache` file