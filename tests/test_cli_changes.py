import json
from hashlib import sha256

from click.testing import CliRunner

from lawdocx import __version__
from lawdocx.cli import main
from tests.docx_factory import create_changes_docx


def test_cli_changes_single_file(tmp_path):
    runner = CliRunner()
    path = create_changes_docx(tmp_path, "changes.docx")

    result = runner.invoke(main, ["changes", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-changes"
    assert payload["lawdocx_version"] == __version__
    assert payload["files"][0]["path"] == str(path)
    assert len(payload["files"][0]["items"]) == 5

    locations = [item["location"] for item in payload["files"][0]["items"]]
    assert all("file_path" not in location for location in locations)
    assert all("file_index" not in location for location in locations)


def test_cli_changes_merge_and_stdin(tmp_path):
    runner = CliRunner()
    one = create_changes_docx(tmp_path, "one.docx")
    two = create_changes_docx(tmp_path, "two.docx")

    data = one.read_bytes()
    expected_hash = sha256(data).hexdigest()

    result = runner.invoke(main, ["changes", str(two), "-"], input=data)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"] == "lawdocx-changes"
    assert len(payload["files"]) == 2

    paths = [entry["path"] for entry in payload["files"]]
    assert set(paths) == {str(two), "stdin"}
    stdin_entry = next(entry for entry in payload["files"] if entry["path"] == "stdin")
    assert stdin_entry["sha256"] == expected_hash
    assert len(stdin_entry["items"]) == 5

    stdin_location = stdin_entry["items"][0]["location"]
    assert "file_path" not in stdin_location
    assert "file_index" not in stdin_location
