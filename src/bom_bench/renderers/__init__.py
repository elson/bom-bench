"""Result renderer orchestration."""

from pathlib import Path

import bom_bench
from bom_bench.logging import get_logger
from bom_bench.models.sca_tool import BenchmarkOverallSummary, BenchmarkSummary
from bom_bench.plugins import pm

logger = get_logger(__name__)


def render_results(
    summaries: list[BenchmarkSummary],
    output_dir: Path,
) -> None:
    """Invoke all registered renderers and write output files.

    Args:
        summaries: List of BenchmarkSummary instances
        output_dir: Base directory for output files
    """
    by_tool: dict[str, list] = {}
    for summary in summaries:
        by_tool.setdefault(summary.tool_name, []).append(summary)

    # Render SCA tool-level results (per fixture set)
    for tool_name, tool_summaries in by_tool.items():
        tool_dir = output_dir / tool_name
        tool_dir.mkdir(parents=True, exist_ok=True)

        tool_dicts = [s.to_dict() for s in tool_summaries]
        for result in pm.hook.register_sca_tool_result_renderer(
            bom_bench=bom_bench,
            tool_name=tool_name,
            summaries=tool_dicts,
        ):
            if result:
                try:
                    filepath = tool_dir / result["filename"]
                    filepath.write_text(result["content"])
                    logger.info(f"Wrote {filepath}")
                except OSError as e:
                    logger.error(f"Failed to write {filepath}: {e}")

    # Compute overall summaries (aggregate across fixture sets per tool)
    overall_summaries = [
        BenchmarkOverallSummary.from_summaries(tool_name, tool_summaries)
        for tool_name, tool_summaries in by_tool.items()
    ]
    overall_dicts = [s.to_dict() for s in overall_summaries]

    # Convert all summaries to dicts for detailed renderers
    all_summary_dicts = [s.to_dict() for s in summaries]

    # Render benchmark-level results (aggregated across all fixture sets)
    for result in pm.hook.register_benchmark_result_renderer(
        bom_bench=bom_bench,
        overall_summaries=overall_dicts,
        summaries=all_summary_dicts,
    ):
        if result:
            try:
                filepath = output_dir / result["filename"]
                filepath.write_text(result["content"])
                logger.info(f"Wrote {filepath}")
            except OSError as e:
                logger.error(f"Failed to write {filepath}: {e}")
