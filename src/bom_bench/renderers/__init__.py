"""Result renderer orchestration."""

from pathlib import Path

import bom_bench
from bom_bench.logging import get_logger
from bom_bench.models.sca_tool import BenchmarkSummary
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
    all_dicts = [s.to_dict() for s in summaries]

    by_tool: dict[str, list[dict]] = {}
    for summary_dict in all_dicts:
        by_tool.setdefault(summary_dict["tool_name"], []).append(summary_dict)

    for tool_name, tool_summaries in by_tool.items():
        tool_dir = output_dir / tool_name
        tool_dir.mkdir(parents=True, exist_ok=True)

        for result in pm.hook.register_sca_tool_result_renderer(
            bom_bench=bom_bench,
            tool_name=tool_name,
            summaries=tool_summaries,
        ):
            if result:
                try:
                    filepath = tool_dir / result["filename"]
                    filepath.write_text(result["content"])
                    logger.info(f"Wrote {filepath}")
                except OSError as e:
                    logger.error(f"Failed to write {filepath}: {e}")

    for result in pm.hook.register_benchmark_result_renderer(
        bom_bench=bom_bench,
        all_summaries=all_dicts,
    ):
        if result:
            try:
                filepath = output_dir / result["filename"]
                filepath.write_text(result["content"])
                logger.info(f"Wrote {filepath}")
            except OSError as e:
                logger.error(f"Failed to write {filepath}: {e}")
