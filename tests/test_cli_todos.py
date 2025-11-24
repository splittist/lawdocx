from __future__ import annotations

import json
from hashlib import sha256

from click.testing import CliRunner

from lawdocx import __version__
from lawdocx.cli import main
from tests.docx_factory import create_boilerplate_docx


def test_cli_todos_single_file(tmp_path):
    runner = CliRunner()
    path = create_boilerplate_docx(
        tmp_path,
        "todos.docx",
        header_text="TODO header",
        footer_text="Footer [TBD]",
        body_paragraphs=["Body needs CHECK"],
    )

    result = runner.invoke(main, ["todos", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-todos"
    assert payload["lawdocx_version"] == __version__
    assert payload["files"][0]["path"] == str(path)
    assert payload["files"][0]["items"]


def test_cli_todos_stdin_merge(tmp_path):
    runner = CliRunner()
    one = create_boilerplate_docx(tmp_path, "one.docx", header_text="TODO item")
    two = create_boilerplate_docx(tmp_path, "two.docx", footer_text="[TBC]")

    data = one.read_bytes()
    expected_hash = sha256(data).hexdigest()

    result = runner.invoke(main, ["todos", str(two), "-"], input=data)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-todos"
    assert len(payload["files"]) == 2

    paths = [entry["path"] for entry in payload["files"]]
    assert set(paths) == {str(two), "stdin"}
    stdin_entry = next(entry for entry in payload["files"] if entry["path"] == "stdin")
    assert stdin_entry["sha256"] == expected_hash
    assert stdin_entry["items"]
