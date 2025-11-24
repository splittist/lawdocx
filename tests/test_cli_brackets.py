from __future__ import annotations

import json

from click.testing import CliRunner

from lawdocx import __version__
from lawdocx.cli import main
from tests.docx_factory import create_boilerplate_docx


def test_cli_brackets_single_file(tmp_path):
    runner = CliRunner()
    path = create_boilerplate_docx(
        tmp_path,
        "cli-brackets.docx",
        header_text="[Header check]",
        footer_text="Footer text",
        body_paragraphs=["Body [content]"],
    )

    result = runner.invoke(main, ["brackets", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-brackets"
    assert payload["lawdocx_version"] == __version__
    assert payload["files"][0]["path"] == str(path)
    assert payload["files"][0]["items"]


def test_cli_brackets_patterns_merge(tmp_path):
    runner = CliRunner()
    one = create_boilerplate_docx(tmp_path, "one.docx", body_paragraphs=["ALERT item"])  # no brackets
    two = create_boilerplate_docx(tmp_path, "two.docx", body_paragraphs=["Another ALERT here"])  # no brackets

    data = one.read_bytes()

    result = runner.invoke(
        main,
        [
            "brackets",
            str(two),
            "-",
            "--pattern",
            "ALERT",
        ],
        input=data,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-brackets"
    assert len(payload["files"]) == 2

    paths = [entry["path"] for entry in payload["files"]]
    assert set(paths) == {str(two), "stdin"}
    stdin_entry = next(entry for entry in payload["files"] if entry["path"] == "stdin")
    assert stdin_entry["items"]


def test_cli_brackets_fail_on_findings_and_severity(tmp_path):
    runner = CliRunner()
    path = create_boilerplate_docx(
        tmp_path, "severity.docx", body_paragraphs=["Please [review] this clause"]
    )

    failing = runner.invoke(
        main, ["brackets", str(path), "--fail-on-findings"], catch_exceptions=False
    )

    assert failing.exit_code == 1
    payload = json.loads(failing.output)
    assert payload["files"][0]["items"]

    filtered = runner.invoke(
        main,
        ["brackets", str(path), "--fail-on-findings", "--severity", "error"],
        catch_exceptions=False,
    )

    assert filtered.exit_code == 0
    filtered_payload = json.loads(filtered.output)
    assert filtered_payload["files"][0]["items"] == []
