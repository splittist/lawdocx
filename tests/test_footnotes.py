import json

from lawdocx.footnotes import collect_footnotes, run_footnotes
from lawdocx.io_utils import InputSource
from tests.docx_factory import create_notes_docx


def _as_dicts(findings):
    return [f.as_dict() for f in findings]


def test_collect_footnotes_and_endnotes(tmp_path):
    path = create_notes_docx(
        tmp_path, "notes.docx", footnote_text="Footnote A", endnote_text="Endnote B"
    )

    findings = _as_dicts(collect_footnotes(str(path)))

    note_types = {item["details"]["note_type"] for item in findings}
    assert note_types == {"footnote", "endnote"}

    footnote = next(item for item in findings if item["details"]["note_type"] == "footnote")
    assert footnote["details"]["note_text"] == "Footnote A"
    assert footnote["context"]["target"] == "[FN 1]"
    assert "Body with footnote" in footnote["context"]["before"] + footnote["context"]["after"]

    endnote = next(item for item in findings if item["details"]["note_type"] == "endnote")
    assert endnote["details"]["note_text"] == "Endnote B"
    assert endnote["context"]["target"] == "[EN 2]"


def test_run_footnotes_emits_envelope(tmp_path):
    path = create_notes_docx(tmp_path, "envelope.docx")
    inputs = [InputSource(path=str(path), handle=open(path, "rb"))]
    try:
        payload = run_footnotes(inputs)
    finally:
        for source in inputs:
            source.handle.close()

    assert payload["tool"] == "lawdocx-footnotes"
    file_entry = payload["files"][0]
    assert file_entry["path"] == str(path)
    assert file_entry["sha256"]
    assert any(item["type"] in {"footnote", "endnote"} for item in file_entry["items"])
