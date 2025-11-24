import json
from hashlib import sha256

from click.testing import CliRunner

from lawdocx import __version__
from lawdocx.cli import main
from tests.docx_factory import create_highlights_docx


def test_cli_highlights_single_file(tmp_path):
    runner = CliRunner()
    path = create_highlights_docx(tmp_path, "highlights.docx")

    result = runner.invoke(main, ["highlights", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-highlights"
    assert payload["lawdocx_version"] == __version__
    assert payload["files"][0]["path"] == str(path)
    assert payload["files"][0]["items"]


def test_cli_highlights_stdin_merge(tmp_path):
    runner = CliRunner()
    one = create_highlights_docx(tmp_path, "one.docx")
    two = create_highlights_docx(tmp_path, "two.docx")

    data = one.read_bytes()
    expected_hash = sha256(data).hexdigest()

    result = runner.invoke(main, ["highlights", str(two), "-"], input=data)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-highlights"
    assert len(payload["files"]) == 2

    paths = [entry["path"] for entry in payload["files"]]
    assert set(paths) == {str(two), "stdin"}
    stdin_entry = next(entry for entry in payload["files"] if entry["path"] == "stdin")
    assert stdin_entry["sha256"] == expected_hash
    assert stdin_entry["items"]
