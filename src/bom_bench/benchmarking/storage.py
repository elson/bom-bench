"""Benchmark result storage and export.

This module handles saving benchmark results in various formats:
- JSON for individual results and summaries
- CSV for spreadsheet analysis
"""

import csv
import json
from pathlib import Path
from typing import Any

from bom_bench.logging_config import get_logger
from bom_bench.models.sca_tool import BenchmarkResult, BenchmarkSummary

logger = get_logger(__name__)


def _serialize_result(result: BenchmarkResult) -> dict[str, Any]:
    """Convert BenchmarkResult to a JSON-serializable dictionary.

    Args:
        result: BenchmarkResult to serialize

    Returns:
        Dictionary suitable for JSON serialization
    """
    data: dict[str, Any] = {
        "scenario_name": result.scenario_name,
        "package_manager": result.package_manager,
        "tool_name": result.tool_name,
        "status": result.status.value,
        "expected_satisfiable": result.expected_satisfiable,
        "error_message": result.error_message,
    }

    # Add paths as strings
    if result.expected_sbom_path:
        data["expected_sbom_path"] = str(result.expected_sbom_path)
    if result.actual_sbom_path:
        data["actual_sbom_path"] = str(result.actual_sbom_path)

    # Add metrics if present
    if result.metrics:
        data["metrics"] = {
            "true_positives": result.metrics.true_positives,
            "false_positives": result.metrics.false_positives,
            "false_negatives": result.metrics.false_negatives,
            "precision": result.metrics.precision,
            "recall": result.metrics.recall,
            "f1_score": result.metrics.f1_score,
            "expected_purls": list(result.metrics.expected_purls),
            "actual_purls": list(result.metrics.actual_purls),
        }

    # Add SBOM result if present
    if result.sbom_result:
        data["sbom_result"] = {
            "tool_name": result.sbom_result.tool_name,
            "status": result.sbom_result.status.value,
            "duration_seconds": result.sbom_result.duration_seconds,
            "exit_code": result.sbom_result.exit_code,
            "error_message": result.sbom_result.error_message,
        }
        if result.sbom_result.sbom_path:
            data["sbom_result"]["sbom_path"] = str(result.sbom_result.sbom_path)

    return data


def _serialize_summary(summary: BenchmarkSummary) -> dict[str, Any]:
    """Convert BenchmarkSummary to a JSON-serializable dictionary.

    Args:
        summary: BenchmarkSummary to serialize

    Returns:
        Dictionary suitable for JSON serialization
    """
    return {
        "package_manager": summary.package_manager,
        "tool_name": summary.tool_name,
        "total_scenarios": summary.total_scenarios,
        "status_breakdown": {
            "successful": summary.successful,
            "sbom_failed": summary.sbom_failed,
            "unsatisfiable": summary.unsatisfiable,
            "parse_errors": summary.parse_errors,
            "missing_expected": summary.missing_expected,
        },
        "metrics": {
            "mean_precision": summary.mean_precision,
            "mean_recall": summary.mean_recall,
            "mean_f1_score": summary.mean_f1_score,
            "median_precision": summary.median_precision,
            "median_recall": summary.median_recall,
            "median_f1_score": summary.median_f1_score,
        },
        "totals": {
            "true_positives": summary.total_true_positives,
            "false_positives": summary.total_false_positives,
            "false_negatives": summary.total_false_negatives,
        },
    }


def save_benchmark_result(result: BenchmarkResult, output_path: Path) -> None:
    """Save individual benchmark result to JSON.

    Args:
        result: BenchmarkResult to save
        output_path: Path to write JSON file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = _serialize_result(result)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.debug(f"Saved benchmark result to {output_path}")


def save_benchmark_summary(summary: BenchmarkSummary, output_path: Path) -> None:
    """Save benchmark summary to JSON.

    Args:
        summary: BenchmarkSummary to save
        output_path: Path to write JSON file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = _serialize_summary(summary)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.debug(f"Saved benchmark summary to {output_path}")


def export_benchmark_csv(results: list[BenchmarkResult], output_path: Path) -> None:
    """Export benchmark results to CSV.

    Creates a CSV with one row per scenario, including:
    - Scenario metadata
    - Status
    - Metrics (TP, FP, FN, Precision, Recall, F1)
    - Duration

    Args:
        results: List of BenchmarkResults to export
        output_path: Path to write CSV file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scenario_name",
        "package_manager",
        "tool_name",
        "status",
        "satisfiable",
        "true_positives",
        "false_positives",
        "false_negatives",
        "precision",
        "recall",
        "f1_score",
        "duration_seconds",
        "error_message",
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row: dict[str, Any] = {
                "scenario_name": result.scenario_name,
                "package_manager": result.package_manager,
                "tool_name": result.tool_name,
                "status": result.status.value,
                "satisfiable": result.expected_satisfiable,
                "error_message": result.error_message or "",
            }

            # Add metrics if present
            if result.metrics:
                row.update(
                    {
                        "true_positives": result.metrics.true_positives,
                        "false_positives": result.metrics.false_positives,
                        "false_negatives": result.metrics.false_negatives,
                        "precision": f"{result.metrics.precision:.4f}",
                        "recall": f"{result.metrics.recall:.4f}",
                        "f1_score": f"{result.metrics.f1_score:.4f}",
                    }
                )
            else:
                row.update(
                    {
                        "true_positives": "",
                        "false_positives": "",
                        "false_negatives": "",
                        "precision": "",
                        "recall": "",
                        "f1_score": "",
                    }
                )

            # Add duration if present
            if result.sbom_result:
                row["duration_seconds"] = f"{result.sbom_result.duration_seconds:.2f}"
            else:
                row["duration_seconds"] = ""

            writer.writerow(row)

    logger.debug(f"Exported {len(results)} results to {output_path}")
