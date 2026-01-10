"""Benchmark TOML renderer plugin."""

import tomlkit

from bom_bench import hookimpl


def _format_metric(value: float) -> str:
    """Format a metric value or return N/A if zero."""
    return f"{value:.4f}" if value > 0 else "N/A"


@hookimpl
def register_benchmark_result_renderer(overall_summaries: list[dict]) -> dict:
    """Render benchmark results as TOML.

    Creates a TOML file with mean/median metrics per SCA tool.

    Args:
        overall_summaries: List of BenchmarkOverallSummary dicts (one per tool)

    Returns:
        Dict with filename and content for benchmark_summary.toml
    """
    doc = tomlkit.document()

    for summary in overall_summaries:
        section = tomlkit.table()
        section["fixture_sets"] = summary["fixture_sets"]
        section["total_scenarios"] = summary["total_scenarios"]
        section["successful"] = summary["successful"]

        section["mean_precision"] = _format_metric(summary["mean_precision"])
        section["mean_recall"] = _format_metric(summary["mean_recall"])
        section["mean_f1_score"] = _format_metric(summary["mean_f1_score"])
        section["median_precision"] = _format_metric(summary["median_precision"])
        section["median_recall"] = _format_metric(summary["median_recall"])
        section["median_f1_score"] = _format_metric(summary["median_f1_score"])

        doc[summary["tool_name"]] = section

    return {
        "filename": "benchmark_summary.toml",
        "content": tomlkit.dumps(doc),
    }
