"""Benchmark CSV renderer plugin."""

import csv
import io
import statistics

from bom_bench import hookimpl


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
        total = sum(s["total_scenarios"] for s in summaries)
        successful = sum(s["successful"] for s in summaries)
        precisions = [s["mean_precision"] for s in summaries if s["successful"] > 0]
        recalls = [s["mean_recall"] for s in summaries if s["successful"] > 0]
        f1s = [s["mean_f1_score"] for s in summaries if s["successful"] > 0]

        writer.writerow(
            [
                tool,
                len(summaries),
                total,
                successful,
                f"{statistics.mean(precisions):.4f}" if precisions else "N/A",
                f"{statistics.mean(recalls):.4f}" if recalls else "N/A",
                f"{statistics.mean(f1s):.4f}" if f1s else "N/A",
                f"{statistics.median(precisions):.4f}" if precisions else "N/A",
                f"{statistics.median(recalls):.4f}" if recalls else "N/A",
                f"{statistics.median(f1s):.4f}" if f1s else "N/A",
            ]
        )

    return {
        "filename": "benchmark_summary.csv",
        "content": output.getvalue(),
    }
