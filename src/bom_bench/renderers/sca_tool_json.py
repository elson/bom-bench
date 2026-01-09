"""SCA tool JSON renderer plugin."""

import json

from bom_bench import hookimpl


@hookimpl
def register_sca_tool_result_renderer(tool_name: str, summaries: list[dict]) -> dict:
    """Render SCA tool results as pretty-printed JSON.

    Creates a JSON file with raw results for all fixture sets scanned by the tool.
    Includes expected vs actual packages for inspection.

    Args:
        tool_name: Name of the SCA tool
        summaries: List of BenchmarkSummary dicts (one per fixture set)

    Returns:
        Dict with filename and content for results.json
    """
    output = {
        "tool": tool_name,
        "fixture_sets": summaries,
    }

    return {
        "filename": "results.json",
        "content": json.dumps(output, indent=2),
    }
