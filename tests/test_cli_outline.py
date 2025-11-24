from __future__ import annotations

import json
from hashlib import sha256

from click.testing import CliRunner

from lawdocx import __version__
from lawdocx.cli import main
from tests.docx_factory import create_outline_docx


def test_cli_outline_single_file(tmp_path):
    runner = CliRunner()
    path = create_outline_docx(tmp_path, "outline.docx")

    result = runner.invoke(main, ["outline", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-outline"
    assert payload["lawdocx_version"] == __version__
    assert payload["files"][0]["path"] == str(path)
    assert payload["files"][0]["items"]


def test_cli_outline_stdin_merge(tmp_path):
    runner = CliRunner()
    one = create_outline_docx(tmp_path, "one.docx")
    two = create_outline_docx(tmp_path, "two.docx")

    data = one.read_bytes()
    expected_hash = sha256(data).hexdigest()

    result = runner.invoke(main, ["outline", str(two), "-"], input=data)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-outline"
    assert len(payload["files"]) == 2

    paths = [entry["path"] for entry in payload["files"]]
    assert set(paths) == {str(two), "stdin"}
    stdin_entry = next(entry for entry in payload["files"] if entry["path"] == "stdin")
    assert stdin_entry["sha256"] == expected_hash
    assert stdin_entry["items"]
