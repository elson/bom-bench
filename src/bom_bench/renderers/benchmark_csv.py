"""Benchmark CSV renderer plugin."""

import csv
import io
import statistics

from bom_bench import hookimpl


def _format_metric(values: list[float], stat_func) -> str:
    """Format a metric value or return N/A if no data."""
    return f"{stat_func(values):.4f}" if values else "N/A"


@hookimpl
def register_benchmark_result_renderer(all_summaries: list[dict]) -> dict:
    """Render benchmark results as CSV.

    Creates a CSV file with mean/median metrics per SCA tool.

    Args:
        all_summaries: All BenchmarkSummary dicts from the run

    Returns:
        Dict with filename and content for benchmark_summary.csv
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "tool",
            "fixture_sets",
            "total_scenarios",
            "successful",
            "mean_precision",
            "mean_recall",
            "mean_f1",
            "median_precision",
            "median_recall",
            "median_f1",
        ]
    )

    by_tool = {}
    for s in all_summaries:
        by_tool.setdefault(s["tool_name"], []).append(s)

    for tool, summaries in by_tool.items():
        successful_summaries = [s for s in summaries if s["successful"] > 0]
        precisions = [s["mean_precision"] for s in successful_summaries]
        recalls = [s["mean_recall"] for s in successful_summaries]
        f1s = [s["mean_f1_score"] for s in successful_summaries]

        writer.writerow(
            [
                tool,
                len(summaries),
                sum(s["total_scenarios"] for s in summaries),
                sum(s["successful"] for s in summaries),
                _format_metric(precisions, statistics.mean),
                _format_metric(recalls, statistics.mean),
                _format_metric(f1s, statistics.mean),
                _format_metric(precisions, statistics.median),
                _format_metric(recalls, statistics.median),
                _format_metric(f1s, statistics.median),
            ]
        )

    return {
        "filename": "benchmark_summary.csv",
        "content": output.getvalue(),
    }
