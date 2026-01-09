"""Benchmark JSON renderer plugin."""

import json

from bom_bench import hookimpl


@hookimpl
def register_benchmark_result_renderer(all_summaries: list[dict]) -> dict:
    """Render benchmark results as pretty-printed JSON.

    Creates a JSON file with all results for all tools, allowing inspection
    of expected vs actual packages for each fixture.

    Args:
        all_summaries: All BenchmarkSummary dicts from the run

    Returns:
        Dict with filename and content for benchmark_results.json
    """
    by_tool = {}
    for s in all_summaries:
        tool = s["tool_name"]
        by_tool.setdefault(tool, []).append(s)

    return {
        "filename": "benchmark_results.json",
        "content": json.dumps({"tools": by_tool}, indent=2),
    }
