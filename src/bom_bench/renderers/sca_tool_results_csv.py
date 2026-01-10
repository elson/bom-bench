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
def register_sca_tool_result_renderer(tool_name: str, summaries: list[dict]) -> dict:
    """Render SCA tool results as CSV using DictWriter.

    Args:
        tool_name: Name of the SCA tool.
        summaries: List of summary dictionaries (one per fixture set).

    Returns:
        Dict with filename and content for results.csv.
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
                # Merge dictionaries to build the full row
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
            "filename": "results.csv",
            "content": output.getvalue(),
        }
