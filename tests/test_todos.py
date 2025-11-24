from __future__ import annotations

import json

from lawdocx.io_utils import InputSource
from lawdocx.todos import collect_todos, run_todos
from tests.docx_factory import create_boilerplate_docx


def _as_dicts(findings):
    return [f.as_dict() for f in findings]


def test_collect_todos_scans_body_header_and_footer(tmp_path):
    path = create_boilerplate_docx(
        tmp_path,
        "todos.docx",
        header_text="TODO header",
        footer_text="Footer [TBD]",
        body_paragraphs=["Body needs CHECK"],
    )

    findings = _as_dicts(collect_todos(str(path)))

    stories = {f["story"] for f in [item["location"] for item in findings]}
    assert stories == {"body", "header", "footer"}

    matched = {item["details"]["matched_pattern"] for item in findings}
    assert "TODO" in matched
    assert "[TBD]" in matched
    assert "CHECK" in matched


def test_collect_todos_deduplicates_patterns(tmp_path):
    path = create_boilerplate_docx(
        tmp_path,
        "dedupe.docx",
        header_text="TODO item",
    )

    findings = _as_dicts(collect_todos(str(path), patterns=[r"TODO", r"TODO"]))

    assert len(findings) == 1
    assert findings[0]["details"]["matched_pattern"] == "TODO"


def test_run_todos_emits_envelope_and_hash(tmp_path):
    path = create_boilerplate_docx(
        tmp_path,
        "envelope.docx",
        footer_text="[confirm with client]",
    )
    inputs = [InputSource(path=str(path), handle=open(path, "rb"))]
    try:
        payload = run_todos(inputs)
    finally:
        for source in inputs:
            source.handle.close()

    assert list(payload.keys()) == ["lawdocx_version", "tool", "generated_at", "files"]
    assert payload["tool"] == "lawdocx-todos"
    file_entry = payload["files"][0]
    assert file_entry["path"] == str(path)
    assert file_entry["sha256"]
    assert any(item["type"] == "todo" for item in file_entry["items"])
