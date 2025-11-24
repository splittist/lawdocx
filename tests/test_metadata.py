"""Unit tests for metadata extraction helpers."""
from __future__ import annotations

from hashlib import sha256
import json

from lawdocx.metadata import collect_metadata, run_metadata
from lawdocx import __version__
from lawdocx.io_utils import InputSource
from tests.docx_factory import create_metadata_docx


def _as_dicts(findings):
    return [f.as_dict() for f in findings]


def test_collect_metadata_includes_all_categories(tmp_path):
    path = create_metadata_docx(tmp_path, "metadata_sample.docx", include_custom=True)

    findings = _as_dicts(collect_metadata(str(path)))

    categories = {f["details"]["category"] for f in findings}
    assert categories == {"core", "extended", "custom", "custom-xml"}

    values = {f["details"]["name"]: f["context"]["target"] for f in findings}
    assert values["title"] == "Sample Title"
    assert values["creator"] == "Author Name"
    assert values["Template"] == "Normal.dotm"
    assert values["CustomNote"] == "Sample value"
    assert values["CustomNumber"] == "123"

    custom_xml_entries = [
        f for f in findings if f["details"]["category"] == "custom-xml"
    ]
    assert custom_xml_entries
    entry = custom_xml_entries[0]
    assert entry["details"]["count"] == 2
    assert entry["details"]["paths"] == [
        "customXml/item1.xml",
        "customXml/item2.xml",
    ]
    assert all("file_index" not in f["location"] for f in findings)


def test_collect_metadata_gracefully_handles_missing_custom_props(tmp_path):
    path = create_metadata_docx(
        tmp_path, "metadata_no_custom.docx", include_custom=False, include_custom_xml=False
    )

    findings = _as_dicts(collect_metadata(str(path)))
    categories = {f["details"]["category"] for f in findings}

    assert categories == {"core", "extended", "custom-xml"}
    assert all(f["details"]["category"] != "custom" for f in findings)
    assert all(f["severity"] == "info" for f in findings)


def test_run_metadata_emits_schema_envelope_and_hash(tmp_path):
    path = create_metadata_docx(tmp_path, "metadata_sample.docx", include_custom=True)
    inputs = [InputSource(path=str(path), handle=open(path, "rb"))]
    try:
        payload = run_metadata(inputs)
    finally:
        for source in inputs:
            source.handle.close()

    assert list(payload.keys()) == ["lawdocx_version", "tool", "generated_at", "files"]
    assert payload["lawdocx_version"] == __version__
    assert payload["tool"] == "lawdocx-metadata"
    assert len(payload["files"]) == 1

    file_entry = payload["files"][0]
    assert list(file_entry.keys()) == ["path", "sha256", "items"]
    assert file_entry["path"] == str(path)

    expected_hash = sha256(path.read_bytes()).hexdigest()
    assert file_entry["sha256"] == expected_hash
    assert any(item["details"]["category"] == "core" for item in file_entry["items"])
    assert any(item["details"]["category"] == "custom" for item in file_entry["items"])
