"""Benchmark TOML renderer plugin."""

import statistics
from typing import Any

import tomlkit

from bom_bench import hookimpl


def _add_metrics(section: Any, values: list[float], name: str) -> None:
    """Add mean and median metrics to a TOML section if values exist."""
    if values:
        section[f"mean_{name}"] = round(statistics.mean(values), 4)
        section[f"median_{name}"] = round(statistics.median(values), 4)


@hookimpl
def register_benchmark_result_renderer(all_summaries: list[dict]) -> dict:
    """Render benchmark results as TOML.

    Creates a TOML file with mean/median metrics per SCA tool.

    Args:
        all_summaries: All BenchmarkSummary dicts from the run

    Returns:
        Dict with filename and content for benchmark_summary.toml
    """
    doc = tomlkit.document()

    by_tool = {}
    for s in all_summaries:
        by_tool.setdefault(s["tool_name"], []).append(s)

    for tool, summaries in by_tool.items():
        section = tomlkit.table()
        section["fixture_sets"] = len(summaries)
        section["total_scenarios"] = sum(s["total_scenarios"] for s in summaries)
        section["successful"] = sum(s["successful"] for s in summaries)

        successful_summaries = [s for s in summaries if s["successful"] > 0]
        _add_metrics(section, [s["mean_precision"] for s in successful_summaries], "precision")
        _add_metrics(section, [s["mean_recall"] for s in successful_summaries], "recall")
        _add_metrics(section, [s["mean_f1_score"] for s in successful_summaries], "f1_score")

        doc[tool] = section

    return {
        "filename": "benchmark_summary.toml",
        "content": tomlkit.dumps(doc),
    }
