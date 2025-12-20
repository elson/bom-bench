"""pyproject.toml generation for UV package manager."""

from typing import List, Optional


def generate_pyproject_toml(
    name: str,
    version: str,
    dependencies: List[str],
    requires_python: Optional[str] = None,
    required_environments: Optional[List[str]] = None
) -> str:
    """Generate complete pyproject.toml content for UV.

    Args:
        name: Project name
        version: Project version
        dependencies: List of dependency requirement strings
        requires_python: Python version requirement (e.g., '>=3.12')
        required_environments: List of required environments for universal resolution

    Returns:
        Complete pyproject.toml file content as a string
    """
    lines = []

    # [project] section
    lines.append("[project]")
    lines.append(f'name = "{name}"')
    lines.append(f'version = "{version}"')

    # Add dependencies
    if dependencies:
        lines.append("dependencies = [")
        for dep in dependencies:
            # Use single quotes to avoid issues with double quotes in markers
            lines.append(f"  '{dep}',")
        lines.append("]")
    else:
        lines.append("dependencies = []")

    # Add requires-python if present
    if requires_python:
        lines.append(f'requires-python = "{requires_python}"')

    # [tool.uv] section for required environments
    if required_environments:
        lines.append("")
        lines.append("[tool.uv]")
        lines.append("required-environments = [")
        for env in required_environments:
            # Use single quotes to avoid issues with double quotes in the environment strings
            lines.append(f"  '{env}',")
        lines.append("]")

    return "\n".join(lines) + "\n"
