from __future__ import annotations

import json

from lawdocx.io_utils import InputSource
from lawdocx.outline import collect_outline, run_outline
from tests.docx_factory import create_outline_docx


def _as_dicts(findings):
    return [f.as_dict() for f in findings]


def test_collect_outline_detects_manual_and_suspicious(tmp_path):
    path = create_outline_docx(tmp_path, "outline.docx")

    findings = _as_dicts(collect_outline(str(path)))

    categories = {(item["details"].get("category"), item["severity"]) for item in findings}
    assert ("manual_numbering", "error") in categories
    assert ("suspicious_numbering", "warning") in categories

    styles = {item["details"].get("style_name") for item in findings}
    assert "Body Text" in styles
    assert "BodyText" in styles or "Body Text" in styles


def test_run_outline_emits_envelope_and_hash(tmp_path):
    path = create_outline_docx(tmp_path, "envelope.docx")
    inputs = [InputSource(path=str(path), handle=open(path, "rb"))]
    try:
        payload = run_outline(inputs)
    finally:
        for source in inputs:
            source.handle.close()

    assert list(payload.keys()) == ["lawdocx_version", "tool", "generated_at", "files"]
    assert payload["tool"] == "lawdocx-outline"
    file_entry = payload["files"][0]
    assert file_entry["path"] == str(path)
    assert file_entry["sha256"]
    assert any(item["details"].get("category") for item in file_entry["items"])
