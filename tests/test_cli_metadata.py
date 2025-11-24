"""CLI integration tests for metadata extraction."""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from click.testing import CliRunner

from lawdocx.cli import main
from lawdocx import __version__
from tests.docx_factory import create_metadata_docx


def test_metadata_glob_and_merge(tmp_path):
    runner = CliRunner()
    create_metadata_docx(tmp_path, "metadata_sample.docx", include_custom=True)
    create_metadata_docx(tmp_path, "metadata_no_custom.docx", include_custom=False)

    pattern = str(tmp_path / "*.docx")

    result = runner.invoke(main, ["metadata", pattern])

    assert result.exit_code == 0

    envelope = json.loads(result.output)
    assert list(envelope.keys()) == ["lawdocx_version", "tool", "generated_at", "files"]
    assert envelope["lawdocx_version"] == __version__
    assert envelope["tool"] == "lawdocx-metadata"

    files = envelope["files"]
    assert len(files) == 2

    resolved_paths = [Path(f["path"]) for f in files]
    assert resolved_paths == sorted(resolved_paths)

    for entry in files:
        assert list(entry.keys()) == ["path", "sha256", "items"]
        assert len(entry["sha256"]) == 64
        assert entry["items"]


def test_metadata_stdin_stdout(tmp_path):
    runner = CliRunner()
    path = create_metadata_docx(tmp_path, "metadata_sample.docx", include_custom=True)
    data = path.read_bytes()
    expected_hash = sha256(data).hexdigest()

    result = runner.invoke(main, ["metadata", "-"], input=data)

    assert result.exit_code == 0
    payload = json.loads(result.output)

    assert list(payload.keys()) == ["lawdocx_version", "tool", "generated_at", "files"]
    file_entry = payload["files"][0]
    assert file_entry["path"] == "stdin"
    assert file_entry["sha256"] == expected_hash
    assert any(item["details"]["category"] == "custom" for item in file_entry["items"])


def test_metadata_outputs_single_merged_envelope(tmp_path):
    runner = CliRunner()
    file_one = create_metadata_docx(tmp_path, "metadata_sample.docx", include_custom=True)
    file_two = create_metadata_docx(tmp_path, "metadata_no_custom.docx", include_custom=False)

    result = runner.invoke(main, ["metadata", str(file_one), str(file_two)])

    assert result.exit_code == 0
    payload = json.loads(result.output)

    paths = [entry["path"] for entry in payload["files"]]
    assert paths == sorted(paths)
    assert set(paths) == {str(file_one), str(file_two)}
    assert all(entry["sha256"] for entry in payload["files"])
    assert all(
        any(item["details"]["category"] == "custom-xml" for item in entry["items"])
        for entry in payload["files"]
    )
