import csv
import io

from bom_bench import hookimpl

CSV_HEADERS = [
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


def _format_metric(value: float) -> str:
    """Format a metric value or return N/A if zero."""
    return f"{value:.4f}" if value > 0 else "N/A"


@hookimpl
def register_benchmark_result_renderer(overall_summaries: list[dict]) -> dict:
    """Render benchmark results as CSV.

    Creates a CSV file with mean/median metrics per SCA tool.

    Args:
        overall_summaries: List of summary dictionaries (one per tool).

    Returns:
        Dict with filename and content for benchmark_summary.csv.
    """
    with io.StringIO() as output:
        writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
        writer.writeheader()

        for s in overall_summaries:
            row_data = {
                "tool": s.get("tool_name"),
                "fixture_sets": s.get("fixture_sets"),
                "total_scenarios": s.get("total_scenarios"),
                "successful": s.get("successful"),
                "mean_precision": _format_metric(s.get("mean_precision", 0)),
                "mean_recall": _format_metric(s.get("mean_recall", 0)),
                "mean_f1": _format_metric(s.get("mean_f1_score", 0)),
                "median_precision": _format_metric(s.get("median_precision", 0)),
                "median_recall": _format_metric(s.get("median_recall", 0)),
                "median_f1": _format_metric(s.get("median_f1_score", 0)),
            }
            writer.writerow(row_data)

        return {
            "filename": "benchmark_summary.csv",
            "content": output.getvalue(),
        }
