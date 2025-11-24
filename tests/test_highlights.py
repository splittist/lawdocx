import json

from lawdocx.highlights import collect_highlights, run_highlights
from lawdocx.io_utils import InputSource
from tests.docx_factory import create_highlights_docx


def _as_dicts(findings):
    return [f.as_dict() for f in findings]


def test_collect_highlights_covers_all_stories(tmp_path):
    path = create_highlights_docx(tmp_path, "highlights.docx")

    findings = _as_dicts(collect_highlights(str(path)))

    stories = {item["location"]["story"] for item in findings}
    assert stories == {"body", "header", "footer", "footnote", "endnote"}

    colors = {item["details"]["highlight_color"] for item in findings}
    assert colors == {"yellow", "green", "cyan", "pink", "blue"}

    targets = {item["context"]["target"] for item in findings}
    assert "body highlight" in targets
    assert "Header highlight" in targets
    assert "Footer highlight" in targets
    assert "Footnote highlight" in targets
    assert "Endnote highlight" in targets


def test_run_highlights_emits_envelope_and_hash(tmp_path):
    path = create_highlights_docx(tmp_path, "envelope.docx")
    inputs = [InputSource(path=str(path), handle=open(path, "rb"))]
    try:
        payload = run_highlights(inputs)
    finally:
        for source in inputs:
            source.handle.close()

    assert list(payload.keys()) == ["lawdocx_version", "tool", "generated_at", "files"]
    assert payload["tool"] == "lawdocx-highlights"
    file_entry = payload["files"][0]
    assert file_entry["path"] == str(path)
    assert file_entry["sha256"]
    assert any(item["type"] == "highlight" for item in file_entry["items"])
