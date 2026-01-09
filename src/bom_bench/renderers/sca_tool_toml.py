"""SCA tool TOML renderer plugin."""

import tomlkit

from bom_bench import hookimpl


@hookimpl
def register_sca_tool_result_renderer(tool_name: str, summaries: list[dict]) -> dict:
    """Render SCA tool results as TOML.

    Creates a TOML file with metrics at the fixture set level.

    Args:
        tool_name: Name of the SCA tool
        summaries: List of BenchmarkSummary dicts (one per fixture set)

    Returns:
        Dict with filename and content for summary.toml
    """
    doc = tomlkit.document()
    doc["tool"] = tool_name

    for s in summaries:
        section = tomlkit.table()
        section["total_scenarios"] = s["total_scenarios"]
        section["successful"] = s["successful"]
        section["mean_precision"] = round(s["mean_precision"], 4)
        section["mean_recall"] = round(s["mean_recall"], 4)
        section["mean_f1_score"] = round(s["mean_f1_score"], 4)
        section["median_precision"] = round(s["median_precision"], 4)
        section["median_recall"] = round(s["median_recall"], 4)
        section["median_f1_score"] = round(s["median_f1_score"], 4)
        doc[s["fixture_set"]] = section

    return {
        "filename": "summary.toml",
        "content": tomlkit.dumps(doc),
    }
