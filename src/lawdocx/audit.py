"""Composite tool that runs all lawdocx analyzers in a single pass."""
from __future__ import annotations

import io
from typing import Callable, Iterable, Sequence

from lawdocx.io_utils import InputSource
from lawdocx.utils import (
    build_envelope,
    filter_files_by_severity,
    summarize_severities,
)

ToolRunner = Callable[[Iterable[InputSource]], dict]


def _clone_inputs(buffered_inputs: Sequence[tuple[InputSource, bytes]]) -> list[InputSource]:
    """Return fresh ``InputSource`` instances backed by in-memory buffers."""

    cloned: list[InputSource] = []
    for source, data in buffered_inputs:
        cloned.append(
            InputSource(
                path=source.path,
                handle=io.BytesIO(data),
                is_stdin=source.is_stdin,
            )
        )
    return cloned


def run_audit(
    inputs: Sequence[InputSource],
    tool_runners: Sequence[tuple[str, ToolRunner]],
    *,
    severity: str,
) -> tuple[dict, dict[str, int]]:
    """Run multiple tools across the provided inputs and wrap their outputs.

    Parameters
    ----------
    inputs:
        The input sources to inspect.
    tool_runners:
        A sequence of ``(name, runner)`` pairs to execute.
    severity:
        Minimum severity to include in each nested tool output.
    """

    buffered_inputs = [(source, source.handle.read()) for source in inputs]
    aggregated_tools: list[dict] = []
    totals = {"info": 0, "warning": 0, "error": 0}

    for _, runner in tool_runners:
        cloned_inputs = _clone_inputs(buffered_inputs)
        envelope = runner(cloned_inputs)
        filtered_files = filter_files_by_severity(envelope.get("files", []), severity)
        envelope = {**envelope, "files": filtered_files}
        aggregated_tools.append(envelope)

        tool_summary = summarize_severities(filtered_files)
        for key, value in tool_summary.items():
            totals[key] += value

    outer = build_envelope(tool="lawdocx-audit", files=[])
    outer["tools"] = aggregated_tools

    return outer, totals
