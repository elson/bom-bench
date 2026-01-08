"""SCA tool plugin management.

Provides functions for working with SCA tools:
    from bom_bench.sca_tools import (
        get_registered_tools,
        get_tool_info,
        get_tool_config,
    )

Available plugins:
- cdxgen: CycloneDX Generator
- syft: Anchore Syft
"""

from typing import Any

from bom_bench.logging import get_logger
from bom_bench.models.sca_tool import SCAToolConfig, SCAToolInfo
from bom_bench.utils import expandvars_dict

logger = get_logger(__name__)

# Track registered tools
_registered_tools: dict[str, SCAToolInfo] = {}
_registered_tool_data: dict[str, dict] = {}
_registered_tool_plugins: dict[str, Any] = {}  # tool_name -> plugin module


def _register_tools(pm) -> None:
    """Register SCA tools from plugins.

    Called by initialize_plugins() in bom_bench.plugins.

    Args:
        pm: The pluggy PluginManager instance
    """
    global _registered_tools, _registered_tool_data, _registered_tool_plugins
    _registered_tools = {}
    _registered_tool_data = {}
    _registered_tool_plugins = {}

    # Iterate over plugins to track which plugin registered each tool
    for plugin in pm.get_plugins():
        # Check if plugin has register_sca_tools method and call it directly
        if hasattr(plugin, "register_sca_tools"):
            tool_data = plugin.register_sca_tools()
            if tool_data:
                # Only expand env vars in the 'env' dict, not in 'args' (which contains runtime placeholders)
                if "env" in tool_data:
                    tool_data["env"] = expandvars_dict(tool_data["env"])
                tool_info = SCAToolInfo.from_dict(tool_data)
                _registered_tools[tool_info.name] = tool_info
                _registered_tool_data[tool_info.name] = tool_data
                _registered_tool_plugins[tool_info.name] = plugin  # Track plugin
                logger.debug(f"Registered SCA tool: {tool_info.name}")


def _reset_tools() -> None:
    """Reset tool registry.

    Called by reset_plugins() in bom_bench.plugins.
    """
    global _registered_tools, _registered_tool_data, _registered_tool_plugins
    _registered_tools = {}
    _registered_tool_data = {}
    _registered_tool_plugins = {}


def get_registered_tools() -> dict[str, SCAToolInfo]:
    """Get all registered SCA tools.

    Returns:
        Dictionary mapping tool name to SCAToolInfo.
    """
    from bom_bench.plugins import initialize_plugins

    initialize_plugins()
    return _registered_tools.copy()


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


def get_tool_plugin(tool_name: str) -> Any | None:
    """Get the plugin module that registered a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Plugin module or None if tool not found
    """
    from bom_bench.plugins import initialize_plugins

    initialize_plugins()
    return _registered_tool_plugins.get(tool_name)


__all__ = [
    "get_registered_tools",
    "get_tool_info",
    "get_tool_config",
    "get_tool_plugin",
]
