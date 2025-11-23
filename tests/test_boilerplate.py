"""Unit tests for boilerplate detection."""
from __future__ import annotations

import json

from lawdocx.boilerplate import collect_boilerplate, run_boilerplate
from lawdocx.io_utils import InputSource
from tests.docx_factory import create_boilerplate_docx


def _as_dicts(findings):
    return [f.as_dict() for f in findings]


def test_collect_boilerplate_scans_only_header_and_footer(tmp_path):
    path = create_boilerplate_docx(
        tmp_path,
        "boilerplate.docx",
        header_text="DRAFT for discussion only",
        footer_text="© 2025 Davis Polk & Wardwell LLP",
        body_paragraphs=["Agreement dated ________", "Page 1 of 3"],
    )

    findings = _as_dicts(collect_boilerplate(str(path)))

    stories = {f["location"]["story"] for f in findings}
    assert stories == {"header", "footer"}

    matched_targets = {f["context"]["target"] for f in findings}
    assert any("DRAFT" in target for target in matched_targets)
    assert any("Davis Polk" in target for target in matched_targets)
    assert all("Page 1 of 3" not in target for target in matched_targets)


def test_collect_boilerplate_supports_custom_patterns(tmp_path):
    path = create_boilerplate_docx(
        tmp_path,
        "custom.docx",
        header_text="SAFE HARBOR NOTICE",
    )

    findings = _as_dicts(collect_boilerplate(str(path), patterns=[r"SAFE HARBOR"]))

    assert len(findings) == 1
    assert findings[0]["details"]["matched_pattern"] == "SAFE HARBOR"
    assert findings[0]["location"]["story"] == "header"


def test_run_boilerplate_emits_envelope_and_hash(tmp_path):
    path = create_boilerplate_docx(
        tmp_path,
        "envelope.docx",
        header_text="For discussion only",
        footer_text="© 2024 Example LLP",
        body_paragraphs=["Dated ________"],
    )
    buffer = tmp_path / "out.jsonl"

    inputs = [InputSource(path=str(path), handle=open(path, "rb"))]
    try:
        with buffer.open("w") as output:
            run_boilerplate(inputs, merge=False, output_handle=output)
    finally:
        for source in inputs:
            source.handle.close()

    payload = json.loads(buffer.read_text())

    assert list(payload.keys()) == ["lawdocx_version", "tool", "generated_at", "files"]
    assert payload["tool"] == "lawdocx-boilerplate"
    file_entry = payload["files"][0]
    assert file_entry["path"] == str(path)
    assert file_entry["sha256"]
    assert any(item["type"] == "boilerplate" for item in file_entry["items"])
