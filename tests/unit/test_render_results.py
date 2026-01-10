"""Tests for render_results function."""

from unittest.mock import patch

from bom_bench.models.sca_tool import BenchmarkSummary
from bom_bench.renderers import render_results


class TestRenderResults:
    """Tests for render_results function."""

    def test_render_results_groups_by_tool(self, tmp_path):
        """Test that summaries are grouped by tool for SCA tool renderers."""
        summary1 = BenchmarkSummary(package_manager="packse", tool_name="cdxgen")
        summary2 = BenchmarkSummary(package_manager="packse2", tool_name="cdxgen")
        summary3 = BenchmarkSummary(package_manager="packse", tool_name="syft")

        with patch("bom_bench.renderers.pm") as mock_pm:
            mock_pm.hook.register_sca_tool_result_renderer.return_value = []
            mock_pm.hook.register_benchmark_result_renderer.return_value = []

            render_results([summary1, summary2, summary3], tmp_path)

            # Should be called once per tool (2 tools)
            assert mock_pm.hook.register_sca_tool_result_renderer.call_count == 2

            # Check cdxgen call
            calls = mock_pm.hook.register_sca_tool_result_renderer.call_args_list
            cdxgen_call = [c for c in calls if c.kwargs["tool_name"] == "cdxgen"][0]
            assert len(cdxgen_call.kwargs["summaries"]) == 2

            # Check syft call
            syft_call = [c for c in calls if c.kwargs["tool_name"] == "syft"][0]
            assert len(syft_call.kwargs["summaries"]) == 1

    def test_render_results_writes_files(self, tmp_path):
        """Test that render results writes files to correct locations."""
        summary = BenchmarkSummary(package_manager="packse", tool_name="cdxgen")

        sca_result = {"filename": "results.json", "content": '{"test": "data"}'}
        benchmark_result = {
            "filename": "benchmark.json",
            "content": '{"benchmark": "data"}',
        }

        with patch("bom_bench.renderers.pm") as mock_pm:
            mock_pm.hook.register_sca_tool_result_renderer.return_value = [sca_result]
            mock_pm.hook.register_benchmark_result_renderer.return_value = [benchmark_result]

            render_results([summary], tmp_path)

            # Check SCA tool file
            sca_file = tmp_path / "cdxgen" / "results.json"
            assert sca_file.exists()
            assert sca_file.read_text() == '{"test": "data"}'

            # Check benchmark file
            benchmark_file = tmp_path / "benchmark.json"
            assert benchmark_file.exists()
            assert benchmark_file.read_text() == '{"benchmark": "data"}'

    def test_render_results_skips_none_results(self, tmp_path):
        """Test that None results from renderers are skipped."""
        summary = BenchmarkSummary(package_manager="packse", tool_name="cdxgen")

        with patch("bom_bench.renderers.pm") as mock_pm:
            # Some renderers return None
            mock_pm.hook.register_sca_tool_result_renderer.return_value = [
                None,
                {"filename": "test.json", "content": "{}"},
                None,
            ]
            mock_pm.hook.register_benchmark_result_renderer.return_value = [None]

            render_results([summary], tmp_path)

            # Only one file should be written
            files = list((tmp_path / "cdxgen").glob("*"))
            assert len(files) == 1
            assert files[0].name == "test.json"

    def test_render_results_creates_tool_directories(self, tmp_path):
        """Test that tool directories are created."""
        summary1 = BenchmarkSummary(package_manager="packse", tool_name="cdxgen")
        summary2 = BenchmarkSummary(package_manager="packse", tool_name="syft")

        with patch("bom_bench.renderers.pm") as mock_pm:
            mock_pm.hook.register_sca_tool_result_renderer.return_value = []
            mock_pm.hook.register_benchmark_result_renderer.return_value = []

            render_results([summary1, summary2], tmp_path)

            assert (tmp_path / "cdxgen").exists()
            assert (tmp_path / "cdxgen").is_dir()
            assert (tmp_path / "syft").exists()
            assert (tmp_path / "syft").is_dir()

    def test_render_results_passes_summary_dicts(self, tmp_path):
        """Test that summaries are converted to dicts before passing to hooks."""
        summary = BenchmarkSummary(package_manager="packse", tool_name="cdxgen")
        summary.successful = 5
        summary.total_scenarios = 10

        with patch("bom_bench.renderers.pm") as mock_pm:
            mock_pm.hook.register_sca_tool_result_renderer.return_value = []
            mock_pm.hook.register_benchmark_result_renderer.return_value = []

            render_results([summary], tmp_path)

            # Check SCA tool renderer was passed dict
            call_kwargs = mock_pm.hook.register_sca_tool_result_renderer.call_args.kwargs
            assert isinstance(call_kwargs["summaries"], list)
            assert isinstance(call_kwargs["summaries"][0], dict)
            assert call_kwargs["summaries"][0]["successful"] == 5
            assert call_kwargs["summaries"][0]["total_scenarios"] == 10

            # Check benchmark renderer was passed overall summary dicts
            call_kwargs = mock_pm.hook.register_benchmark_result_renderer.call_args.kwargs
            assert isinstance(call_kwargs["overall_summaries"], list)
            assert isinstance(call_kwargs["overall_summaries"][0], dict)
            # Overall summary should have aggregated data
            assert call_kwargs["overall_summaries"][0]["tool_name"] == "cdxgen"
            assert call_kwargs["overall_summaries"][0]["fixture_sets"] == 1
