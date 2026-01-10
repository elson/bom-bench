"""Tests for benchmark_results_csv renderer plugin."""

import csv
import io

from bom_bench.renderers.benchmark_results_csv import register_benchmark_result_renderer


class TestBenchmarkResultsCSVRenderer:
    """Tests for benchmark detailed results CSV renderer."""

    def test_returns_dict_with_filename_and_content(self):
        """Test that renderer returns dict with required keys."""
        summaries = []
        result = register_benchmark_result_renderer(summaries)

        assert isinstance(result, dict)
        assert "filename" in result
        assert "content" in result

    def test_filename_is_benchmark_results_csv(self):
        """Test that output filename is benchmark_results.csv."""
        summaries = []
        result = register_benchmark_result_renderer(summaries)

        assert result["filename"] == "benchmark_results.csv"

    def test_content_is_valid_csv(self):
        """Test that content is valid CSV format."""
        summaries = [
            {
                "tool_name": "cdxgen",
                "fixture_set": "packse",
                "results": [
                    {
                        "scenario_name": "fork-basic",
                        "status": "success",
                        "metrics": {
                            "true_positives": 5,
                            "false_positives": 0,
                            "false_negatives": 0,
                            "precision": 1.0,
                            "recall": 1.0,
                            "f1_score": 1.0,
                            "expected_purls": ["pkg:pypi/foo@1.0"],
                            "actual_purls": ["pkg:pypi/foo@1.0"],
                        },
                    }
                ],
            }
        ]

        result = register_benchmark_result_renderer(summaries)

        # Should parse without errors
        reader = csv.DictReader(io.StringIO(result["content"]))
        rows = list(reader)
        assert len(rows) == 1

    def test_includes_all_tools(self):
        """Test that CSV includes results from multiple tools."""
        summaries = [
            {
                "tool_name": "cdxgen",
                "fixture_set": "packse",
                "results": [{"scenario_name": "test1", "status": "success", "metrics": None}],
            },
            {
                "tool_name": "syft",
                "fixture_set": "packse",
                "results": [{"scenario_name": "test2", "status": "success", "metrics": None}],
            },
        ]

        result = register_benchmark_result_renderer(summaries)

        reader = csv.DictReader(io.StringIO(result["content"]))
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["tool_name"] == "cdxgen"
        assert rows[1]["tool_name"] == "syft"

    def test_includes_all_fixture_sets(self):
        """Test that CSV includes results from multiple fixture sets."""
        summaries = [
            {
                "tool_name": "cdxgen",
                "fixture_set": "packse",
                "results": [{"scenario_name": "test1", "status": "success", "metrics": None}],
            },
            {
                "tool_name": "cdxgen",
                "fixture_set": "npm",
                "results": [{"scenario_name": "test2", "status": "success", "metrics": None}],
            },
        ]

        result = register_benchmark_result_renderer(summaries)

        reader = csv.DictReader(io.StringIO(result["content"]))
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["fixture_set"] == "packse"
        assert rows[1]["fixture_set"] == "npm"

    def test_formats_metrics_correctly(self):
        """Test that metrics are formatted with correct precision."""
        summaries = [
            {
                "tool_name": "cdxgen",
                "fixture_set": "packse",
                "results": [
                    {
                        "scenario_name": "test",
                        "status": "success",
                        "metrics": {
                            "true_positives": 8,
                            "false_positives": 1,
                            "false_negatives": 2,
                            "precision": 0.88889,
                            "recall": 0.8,
                            "f1_score": 0.84211,
                            "expected_purls": [],
                            "actual_purls": [],
                        },
                    }
                ],
            }
        ]

        result = register_benchmark_result_renderer(summaries)

        reader = csv.DictReader(io.StringIO(result["content"]))
        rows = list(reader)

        assert rows[0]["precision"] == "0.8889"
        assert rows[0]["recall"] == "0.8000"
        assert rows[0]["f1_score"] == "0.8421"

    def test_handles_missing_metrics(self):
        """Test that missing metrics are handled gracefully."""
        summaries = [
            {
                "tool_name": "cdxgen",
                "fixture_set": "packse",
                "results": [
                    {
                        "scenario_name": "failed",
                        "status": "sbom_failed",
                        "metrics": None,
                        "error_message": "Tool failed",
                    }
                ],
            }
        ]

        result = register_benchmark_result_renderer(summaries)

        reader = csv.DictReader(io.StringIO(result["content"]))
        rows = list(reader)

        assert rows[0]["precision"] == ""
        assert rows[0]["recall"] == ""
        assert rows[0]["f1_score"] == ""
        assert rows[0]["error_message"] == "Tool failed"

    def test_includes_purls(self):
        """Test that PURLs are included and semicolon-separated."""
        summaries = [
            {
                "tool_name": "cdxgen",
                "fixture_set": "packse",
                "results": [
                    {
                        "scenario_name": "test",
                        "status": "success",
                        "metrics": {
                            "true_positives": 2,
                            "false_positives": 0,
                            "false_negatives": 0,
                            "precision": 1.0,
                            "recall": 1.0,
                            "f1_score": 1.0,
                            "expected_purls": ["pkg:pypi/foo@1.0", "pkg:pypi/bar@2.0"],
                            "actual_purls": ["pkg:pypi/foo@1.0", "pkg:pypi/bar@2.0"],
                        },
                    }
                ],
            }
        ]

        result = register_benchmark_result_renderer(summaries)

        reader = csv.DictReader(io.StringIO(result["content"]))
        rows = list(reader)

        assert rows[0]["expected_purls"] == "pkg:pypi/foo@1.0;pkg:pypi/bar@2.0"
        assert rows[0]["actual_purls"] == "pkg:pypi/foo@1.0;pkg:pypi/bar@2.0"

    def test_empty_summaries_produces_empty_csv(self):
        """Test that empty summaries list produces CSV with just headers."""
        summaries = []

        result = register_benchmark_result_renderer(summaries)

        reader = csv.DictReader(io.StringIO(result["content"]))
        rows = list(reader)

        assert len(rows) == 0
        # But headers should still be present
        assert reader.fieldnames is not None
