"""SCA tool plugin management.

Provides functions for working with SCA tools:
    from bom_bench.sca_tools import (
        get_registered_tools,
        list_available_tools,
        check_tool_available,
        generate_sbom,
    )

Available plugins:
- cdxgen: CycloneDX Generator
- syft: Anchore Syft
"""

from pathlib import Path

from bom_bench.logging import get_logger
from bom_bench.models.sca_tool import ScanResult, SCAToolConfig, SCAToolInfo

logger = get_logger(__name__)

# Track registered tools
_registered_tools: dict[str, SCAToolInfo] = {}
_registered_tool_data: dict[str, dict] = {}


def _register_tools(pm) -> None:
    """Register SCA tools from plugins.

    Called by initialize_plugins() in bom_bench.plugins.

    Args:
        pm: The pluggy PluginManager instance
    """
    global _registered_tools, _registered_tool_data
    _registered_tools = {}
    _registered_tool_data = {}

    # Each plugin returns a single dict, which we convert to SCAToolInfo
    for tool_data in pm.hook.register_sca_tools():
        if tool_data:
            tool_info = SCAToolInfo.from_dict(tool_data)
            _registered_tools[tool_info.name] = tool_info
            _registered_tool_data[tool_info.name] = tool_data
            logger.debug(f"Registered SCA tool: {tool_info.name}")


def _reset_tools() -> None:
    """Reset tool registry.

    Called by reset_plugins() in bom_bench.plugins.
    """
    global _registered_tools, _registered_tool_data
    _registered_tools = {}
    _registered_tool_data = {}


def get_registered_tools() -> dict[str, SCAToolInfo]:
    """Get all registered SCA tools.

    Returns:
        Dictionary mapping tool name to SCAToolInfo.
    """
    from bom_bench.plugins import initialize_plugins

    initialize_plugins()
    return _registered_tools.copy()


def list_available_tools() -> list[str]:
    """Get list of available tool names.

    Returns:
        List of registered tool names.
    """
    return list(get_registered_tools().keys())


def get_tool_info(tool_name: str) -> SCAToolInfo | None:
    """Get info for a specific tool.

    Args:
        tool_name: Name of the tool.

    Returns:
        SCAToolInfo or None if tool not registered.
    """
    return get_registered_tools().get(tool_name)


def get_tool_config(tool_name: str) -> SCAToolConfig | None:
    """Get declarative config for a specific tool.

    Returns the SCAToolConfig needed for sandbox execution.

    Args:
        tool_name: Name of the tool.

    Returns:
        SCAToolConfig or None if tool not registered or lacks config.
    """
    from bom_bench.plugins import initialize_plugins

    initialize_plugins()

    tool_data = _registered_tool_data.get(tool_name)
    if not tool_data:
        return None

    # Check if tool has declarative config
    if "command" not in tool_data:
        logger.warning(f"Tool '{tool_name}' does not have declarative config")
        return None

    return SCAToolConfig.from_dict(tool_data)


def check_tool_available(tool_name: str) -> bool:
    """Check if a specific tool is installed and available.

    Uses the 'installed' field from tool registration.

    Args:
        tool_name: Name of the tool to check.

    Returns:
        True if tool is available, False otherwise.
    """
    tools = get_registered_tools()
    if tool_name not in tools:
        return False
    return tools[tool_name].installed


def scan_project(
    tool_name: str, project_dir: Path, output_path: Path, ecosystem: str, timeout: int = 120
) -> ScanResult | None:
    """Scan project using a registered tool to generate SBOM.

    Args:
        tool_name: Name of the SCA tool to use.
        project_dir: Directory containing project files.
        output_path: Where to write the SBOM.
        ecosystem: Package ecosystem (python, javascript, etc.)
        timeout: Execution timeout in seconds.

    Returns:
        ScanResult with execution details, or None if tool not found.
    """
    from bom_bench.plugins import initialize_plugins, pm

    initialize_plugins()

    if tool_name not in _registered_tools:
        logger.warning(f"Tool '{tool_name}' not registered")
        return None

    results = pm.hook.scan_project(
        tool_name=tool_name,
        project_dir=project_dir,
        output_path=output_path,
        ecosystem=ecosystem,
        timeout=timeout,
    )

    # Plugins return dicts, convert to ScanResult
    for result in results:
        if result is not None:
            return ScanResult.from_dict(result)

    logger.warning(f"No plugin handled project scan for tool '{tool_name}'")
    return None


__all__ = [
    "get_registered_tools",
    "list_available_tools",
    "get_tool_info",
    "get_tool_config",
    "check_tool_available",
    "scan_project",
]
