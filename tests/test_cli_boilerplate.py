"""CLI integration tests for boilerplate detection."""
from __future__ import annotations

import json
from hashlib import sha256

from click.testing import CliRunner

from lawdocx.cli import main
from lawdocx import __version__
from tests.docx_factory import create_boilerplate_docx


def test_cli_boilerplate_single_file(tmp_path):
    runner = CliRunner()
    path = create_boilerplate_docx(
        tmp_path,
        "boilerplate.docx",
        header_text="Draft for discussion",
        footer_text="© 2025 Example LLP",
        body_paragraphs=["Page 2 of 10"],
    )

    result = runner.invoke(main, ["boilerplate", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-boilerplate"
    assert payload["lawdocx_version"] == __version__
    assert payload["files"][0]["path"] == str(path)
    assert payload["files"][0]["items"]


def test_cli_boilerplate_stdin_merge(tmp_path):
    runner = CliRunner()
    one = create_boilerplate_docx(tmp_path, "one.docx", header_text="Draft only")
    two = create_boilerplate_docx(tmp_path, "two.docx", footer_text="Page 3 of 5")

    data = one.read_bytes()
    expected_hash = sha256(data).hexdigest()

    result = runner.invoke(main, ["boilerplate", str(two), "-"], input=data)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-boilerplate"
    assert len(payload["files"]) == 2

    paths = [entry["path"] for entry in payload["files"]]
    assert set(paths) == {str(two), "stdin"}
    stdin_entry = next(entry for entry in payload["files"] if entry["path"] == "stdin")
    assert stdin_entry["sha256"] == expected_hash
    assert stdin_entry["items"]
