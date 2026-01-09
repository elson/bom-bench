"""Benchmark TOML renderer plugin."""

import statistics

import tomlkit

from bom_bench import hookimpl


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

        precisions = [s["mean_precision"] for s in summaries if s["successful"] > 0]
        recalls = [s["mean_recall"] for s in summaries if s["successful"] > 0]
        f1s = [s["mean_f1_score"] for s in summaries if s["successful"] > 0]

        if precisions:
            section["mean_precision"] = round(statistics.mean(precisions), 4)
            section["median_precision"] = round(statistics.median(precisions), 4)

        if recalls:
            section["mean_recall"] = round(statistics.mean(recalls), 4)
            section["median_recall"] = round(statistics.median(recalls), 4)

        if f1s:
            section["mean_f1_score"] = round(statistics.mean(f1s), 4)
            section["median_f1_score"] = round(statistics.median(f1s), 4)

        doc[tool] = section

    return {
        "filename": "benchmark_summary.toml",
        "content": tomlkit.dumps(doc),
    }
