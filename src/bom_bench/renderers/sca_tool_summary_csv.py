"""SCA tool CSV renderer plugin."""

import csv
import io

from bom_bench import hookimpl


@hookimpl
def register_sca_tool_result_renderer(tool_name: str, summaries: list[dict]) -> dict:
    """Render SCA tool results as CSV.

    Creates a CSV file with metrics at the fixture set level.

    Args:
        tool_name: Name of the SCA tool
        summaries: List of BenchmarkSummary dicts (one per fixture set)

    Returns:
        Dict with filename and content for summary.csv
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "fixture_set",
            "total",
            "successful",
            "failed",
            "mean_precision",
            "mean_recall",
            "mean_f1",
            "median_precision",
            "median_recall",
            "median_f1",
        ]
    )

    for s in summaries:
        writer.writerow(
            [
                s["fixture_set"],
                s["total_scenarios"],
                s["successful"],
                s["sbom_failed"] + s["parse_errors"],
                f"{s['mean_precision']:.4f}",
                f"{s['mean_recall']:.4f}",
                f"{s['mean_f1_score']:.4f}",
                f"{s['median_precision']:.4f}",
                f"{s['median_recall']:.4f}",
                f"{s['median_f1_score']:.4f}",
            ]
        )

    return {
        "filename": "summary.csv",
        "content": output.getvalue(),
    }
