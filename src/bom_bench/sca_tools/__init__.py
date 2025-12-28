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
from typing import Dict, List, Optional

from bom_bench.logging_config import get_logger
from bom_bench.models.sca import SCAToolInfo, SBOMResult

logger = get_logger(__name__)

# Track registered tools
_registered_tools: Dict[str, SCAToolInfo] = {}


def _register_tools(pm) -> None:
    """Register SCA tools from plugins.

    Called by initialize_plugins() in bom_bench.plugins.

    Args:
        pm: The pluggy PluginManager instance
    """
    global _registered_tools
    _registered_tools = {}

    # Each plugin returns a single dict, which we convert to SCAToolInfo
    tool_results = pm.hook.register_sca_tools()
    for tool_data in tool_results:
        if tool_data:
            tool_info = SCAToolInfo.from_dict(tool_data)
            _registered_tools[tool_info.name] = tool_info
            logger.debug(f"Registered SCA tool: {tool_info.name}")


def _reset_tools() -> None:
    """Reset tool registry.

    Called by reset_plugins() in bom_bench.plugins.
    """
    global _registered_tools
    _registered_tools = {}


def get_registered_tools() -> Dict[str, SCAToolInfo]:
    """Get all registered SCA tools.

    Returns:
        Dictionary mapping tool name to SCAToolInfo.
    """
    from bom_bench.plugins import initialize_plugins
    initialize_plugins()
    return _registered_tools.copy()


def list_available_tools() -> List[str]:
    """Get list of available tool names.

    Returns:
        List of registered tool names.
    """
    return list(get_registered_tools().keys())


def get_tool_info(tool_name: str) -> Optional[SCAToolInfo]:
    """Get info for a specific tool.

    Args:
        tool_name: Name of the tool.

    Returns:
        SCAToolInfo or None if tool not registered.
    """
    return get_registered_tools().get(tool_name)


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


def generate_sbom(
    tool_name: str,
    project_dir: Path,
    output_path: Path,
    ecosystem: str,
    timeout: int = 120
) -> Optional[SBOMResult]:
    """Generate SBOM using a registered tool.

    Args:
        tool_name: Name of the SCA tool to use.
        project_dir: Directory containing project files.
        output_path: Where to write the SBOM.
        ecosystem: Package ecosystem (python, javascript, etc.)
        timeout: Execution timeout in seconds.

    Returns:
        SBOMResult with execution details, or None if tool not found.
    """
    from bom_bench.plugins import pm, initialize_plugins

    initialize_plugins()

    if tool_name not in _registered_tools:
        logger.warning(f"Tool '{tool_name}' not registered")
        return None

    results = pm.hook.generate_sbom(
        tool_name=tool_name,
        project_dir=project_dir,
        output_path=output_path,
        ecosystem=ecosystem,
        timeout=timeout
    )

    # Plugins return dicts, convert to SBOMResult
    for result in results:
        if result is not None:
            return SBOMResult.from_dict(result)

    logger.warning(f"No plugin handled SBOM generation for tool '{tool_name}'")
    return None


__all__ = [
    "get_registered_tools",
    "list_available_tools",
    "get_tool_info",
    "check_tool_available",
    "generate_sbom",
]
