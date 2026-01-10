"""Benchmark detailed results CSV renderer plugin."""

import csv
import io
from typing import Any

from bom_bench import hookimpl

CSV_HEADERS = [
    "tool_name",
    "fixture_set",
    "scenario_name",
    "status",
    "true_positives",
    "false_positives",
    "false_negatives",
    "precision",
    "recall",
    "f1_score",
    "actual_purls",
    "expected_purls",
    "actual_sbom_path",
    "expected_sbom_path",
    "expected_satisfiable",
    "error_message",
]


def _format_metrics(metrics: dict | None) -> dict[str, Any]:
    """Format metric values for CSV output, handling missing data gracefully."""
    if not metrics:
        return dict.fromkeys(
            [
                "true_positives",
                "false_positives",
                "false_negatives",
                "precision",
                "recall",
                "f1_score",
                "actual_purls",
                "expected_purls",
            ],
            "",
        )

    return {
        "true_positives": metrics.get("true_positives"),
        "false_positives": metrics.get("false_positives"),
        "false_negatives": metrics.get("false_negatives"),
        "precision": f"{metrics.get('precision', 0):.4f}",
        "recall": f"{metrics.get('recall', 0):.4f}",
        "f1_score": f"{metrics.get('f1_score', 0):.4f}",
        "actual_purls": ";".join(metrics.get("actual_purls", [])),
        "expected_purls": ";".join(metrics.get("expected_purls", [])),
    }


@hookimpl
def register_benchmark_result_renderer(summaries: list[dict]) -> dict:
    """Render detailed benchmark results as CSV across all tools.

    Creates a CSV file with one row per scenario result, including all tools.

    Args:
        summaries: List of all BenchmarkSummary dicts (all tools, all fixture sets)

    Returns:
        Dict with filename and content for benchmark_results.csv
    """
    with io.StringIO() as output:
        writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
        writer.writeheader()

        for summary in summaries:
            base_info = {
                "tool_name": summary.get("tool_name"),
                "fixture_set": summary.get("fixture_set"),
            }

            for result in summary.get("results", []):
                row_data = {
                    **base_info,
                    **_format_metrics(result.get("metrics")),
                    "scenario_name": result.get("scenario_name"),
                    "status": result.get("status"),
                    "actual_sbom_path": result.get("actual_sbom_path"),
                    "expected_sbom_path": result.get("expected_sbom_path"),
                    "expected_satisfiable": result.get("expected_satisfiable"),
                    "error_message": result.get("error_message"),
                }
                writer.writerow(row_data)

        return {
            "filename": "benchmark_results.csv",
            "content": output.getvalue(),
        }
