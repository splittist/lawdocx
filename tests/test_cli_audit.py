"""CLI integration tests for the audit command."""
from __future__ import annotations

import json

from click.testing import CliRunner

from lawdocx.cli import main
from tests.docx_factory import create_boilerplate_docx


def test_audit_wraps_tool_outputs(tmp_path):
    runner = CliRunner()
    path = create_boilerplate_docx(
        tmp_path,
        "audit.docx",
        header_text="TODO item",
        body_paragraphs=["Simple body"],
    )

    result = runner.invoke(main, ["audit", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)

    assert payload["tool"] == "lawdocx-audit"
    tool_names = [entry["tool"] for entry in payload["tools"]]
    for expected in [
        "lawdocx-metadata",
        "lawdocx-boilerplate",
        "lawdocx-todos",
        "lawdocx-footnotes",
        "lawdocx-changes",
        "lawdocx-comments",
        "lawdocx-highlights",
        "lawdocx-brackets",
        "lawdocx-outline",
    ]:
        assert expected in tool_names


def test_audit_can_filter_tools(tmp_path):
    runner = CliRunner()
    path = create_boilerplate_docx(tmp_path, "audit_only.docx")

    result = runner.invoke(
        main, ["audit", "--only", "metadata", "--only", "todos", str(path)]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    tool_names = [entry["tool"] for entry in payload["tools"]]
    assert tool_names == ["lawdocx-metadata", "lawdocx-todos"]

    result_exclude = runner.invoke(
        main, ["audit", "--exclude", "metadata", str(path)]
    )

    assert result_exclude.exit_code == 0
    payload_exclude = json.loads(result_exclude.output)
    excluded_names = [entry["tool"] for entry in payload_exclude["tools"]]
    assert "lawdocx-metadata" not in excluded_names


def test_audit_fail_on_findings(tmp_path):
    runner = CliRunner()
    path = create_boilerplate_docx(tmp_path, "audit_fail.docx", header_text="TODO this")

    result = runner.invoke(main, ["audit", "--fail-on-findings", str(path)])

    assert result.exit_code == 1
