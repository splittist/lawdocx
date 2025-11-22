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

    result = runner.invoke(main, ["metadata", pattern, "--merge"])

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


def test_metadata_non_merge_outputs_one_envelope_per_file(tmp_path):
    runner = CliRunner()
    file_one = create_metadata_docx(tmp_path, "metadata_sample.docx", include_custom=True)
    file_two = create_metadata_docx(tmp_path, "metadata_no_custom.docx", include_custom=False)

    result = runner.invoke(main, ["metadata", str(file_one), str(file_two)])

    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) == 2

    first_payload = json.loads(lines[0])
    second_payload = json.loads(lines[1])

    assert first_payload["files"][0]["path"] == str(file_one)
    assert second_payload["files"][0]["path"] == str(file_two)
    assert first_payload["files"][0]["sha256"]
    assert second_payload["files"][0]["sha256"]
    assert any(item["details"]["category"] == "revision" for item in first_payload["files"][0]["items"])
    assert any(item["details"]["category"] == "revision" for item in second_payload["files"][0]["items"])
