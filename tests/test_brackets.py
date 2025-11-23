from __future__ import annotations

from lawdocx.brackets import collect_brackets
from tests.docx_factory import create_boilerplate_docx, create_notes_docx


def test_collect_brackets_across_stories(tmp_path):
    path = create_boilerplate_docx(
        tmp_path,
        "brackets.docx",
        header_text="[Header note]",
        footer_text="[Footer text]",
        body_paragraphs=["Body with [outer [inner] brackets] present."],
    )

    findings = collect_brackets(str(path))

    stories = {finding.location["story"] for finding in findings}
    assert {"body", "header", "footer"}.issubset(stories)

    body_targets = {
        finding.context["target"]
        for finding in findings
        if finding.location["story"] == "body"
    }
    assert "[inner]" in body_targets
    assert "[outer [inner] brackets]" in body_targets


def test_collect_brackets_notes(tmp_path):
    path = create_notes_docx(
        tmp_path,
        "notes-brackets.docx",
        footnote_text="Footnote [text] here",
        endnote_text="Endnote [value]",
    )

    findings = collect_brackets(str(path))

    stories = {finding.location["story"] for finding in findings}
    assert {"footnote", "endnote"}.issubset(stories)

    note_targets = {
        finding.context["target"]
        for finding in findings
        if finding.location["story"] in {"footnote", "endnote"}
    }
    assert "[text]" in note_targets
    assert "[value]" in note_targets


def test_collect_brackets_custom_multiline_pattern(tmp_path):
    path = create_boilerplate_docx(
        tmp_path,
        "multiline.docx",
        header_text="",
        footer_text="",
        body_paragraphs=["First line", "continues on the next"],
    )

    pattern = r"First line\ncontinues on the next"
    findings = collect_brackets(str(path), patterns=[pattern])

    assert findings
    assert any(
        finding.details["matched_pattern"] == pattern
        and finding.location["paragraph_index_start"] == 0
        and finding.location["paragraph_index_end"] == 1
        for finding in findings
    )
