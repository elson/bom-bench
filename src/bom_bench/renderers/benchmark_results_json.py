"""Benchmark JSON renderer plugin."""

import json

from bom_bench import hookimpl


@hookimpl
def register_benchmark_result_renderer(overall_summaries: list[dict]) -> dict:
    """Render benchmark results as pretty-printed JSON.

    Creates a JSON file with aggregated metrics for all tools.

    Args:
        overall_summaries: List of BenchmarkOverallSummary dicts (one per tool)

    Returns:
        Dict with filename and content for benchmark_results.json
    """
    by_tool = {s["tool_name"]: s for s in overall_summaries}

    return {
        "filename": "benchmark_results.json",
        "content": json.dumps({"tools": by_tool}, indent=2),
    }
