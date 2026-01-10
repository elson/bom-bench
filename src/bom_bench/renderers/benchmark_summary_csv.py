"""Benchmark CSV renderer plugin."""

import csv
import io

from bom_bench import hookimpl


def _format_metric(value: float) -> str:
    """Format a metric value or return N/A if zero."""
    return f"{value:.4f}" if value > 0 else "N/A"


@hookimpl
def register_benchmark_result_renderer(overall_summaries: list[dict]) -> dict:
    """Render benchmark results as CSV.

    Creates a CSV file with mean/median metrics per SCA tool.

    Args:
        overall_summaries: List of BenchmarkOverallSummary dicts (one per tool)

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

    for summary in overall_summaries:
        writer.writerow(
            [
                summary["tool_name"],
                summary["fixture_sets"],
                summary["total_scenarios"],
                summary["successful"],
                _format_metric(summary["mean_precision"]),
                _format_metric(summary["mean_recall"]),
                _format_metric(summary["mean_f1_score"]),
                _format_metric(summary["median_precision"]),
                _format_metric(summary["median_recall"]),
                _format_metric(summary["median_f1_score"]),
            ]
        )

    return {
        "filename": "benchmark_summary.csv",
        "content": output.getvalue(),
    }
