import csv
import io

from bom_bench import hookimpl

CSV_HEADERS = [
    "fixture_set",
    "total",
    "successful",
    "failed",
    "mean_precision",
    "mean_recall",
    "mean_f1_score",
    "median_precision",
    "median_recall",
    "median_f1_score",
]


@hookimpl
def register_sca_tool_result_renderer(tool_name: str, summaries: list[dict]) -> dict:
    """Render SCA tool results as CSV.

    Creates a CSV file with metrics at the fixture set level.

    Args:
        tool_name: Name of the SCA tool.
        summaries: List of summary dictionaries.

    Returns:
        Dict with filename and content for summary.csv.
    """
    with io.StringIO() as output:
        writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
        writer.writeheader()

        for s in summaries:
            row_data = {
                "fixture_set": s.get("fixture_set"),
                "total": s.get("total_scenarios"),
                "successful": s.get("successful"),
                "failed": s.get("sbom_failed", 0) + s.get("parse_errors", 0),
                "mean_precision": f"{s.get('mean_precision', 0):.4f}",
                "mean_recall": f"{s.get('mean_recall', 0):.4f}",
                "mean_f1_score": f"{s.get('mean_f1_score', 0):.4f}",
                "median_precision": f"{s.get('median_precision', 0):.4f}",
                "median_recall": f"{s.get('median_recall', 0):.4f}",
                "median_f1_score": f"{s.get('median_f1_score', 0):.4f}",
            }
            writer.writerow(row_data)

        return {
            "filename": "summary.csv",
            "content": output.getvalue(),
        }
