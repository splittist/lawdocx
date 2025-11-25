import json

from lawdocx.comments import collect_comments, run_comments
from lawdocx.io_utils import InputSource
from tests.docx_factory import create_comments_docx


def _as_dicts(findings):
    return [f.as_dict() for f in findings]


def test_collect_comments_with_extended_data(tmp_path):
    path = create_comments_docx(tmp_path, "comments.docx")

    findings = _as_dicts(collect_comments(str(path)))

    assert len(findings) == 2
    parent = next(item for item in findings if item["location"]["comment_id"] == "1")
    child = next(item for item in findings if item["location"]["comment_id"] == "2")

    assert parent["details"]["resolved"] is True
    assert parent["details"]["author"] == "Alice"
    assert parent["details"]["initials"] == "AL"
    assert parent["details"]["comment_text"] == "Parent comment\nSecond paragraph"
    assert parent["location"]["story"] == "body"
    assert parent["location"]["paragraph_index_start"] == 0
    assert parent["location"]["paragraph_index_end"] == 0
    assert parent["location"]["target_location"]["story"] == "comment"
    assert parent["location"]["target_location"]["paragraph_index_end"] == 1
    assert parent["context"]["target"] == "parent range"
    assert parent["context"]["before"].endswith("Body with ")
    assert parent["context"]["after"].startswith("")

    assert child["details"].get("parent_comment_id") == "1"
    assert child["details"]["resolved"] is False
    assert child["details"]["comment_text"] == "Child comment"
    assert child["details"].get("context_fallback") is None
    assert child["location"]["story"] == "body"
    assert child["location"]["paragraph_index_start"] == 1
    assert child["location"]["paragraph_index_end"] == 1
    assert child["location"]["target_location"]["paragraph_index_start"] == 0
    assert child["context"]["target"] == "child range"
    assert "More text before" in child["context"]["before"]
    assert child["context"]["after"].startswith(" after comment")


def test_run_comments_emits_envelope(tmp_path):
    path = create_comments_docx(tmp_path, "cli-comments.docx")
    inputs = [InputSource(path=str(path), handle=open(path, "rb"))]
    try:
        payload = run_comments(inputs)
    finally:
        for source in inputs:
            source.handle.close()

    assert payload["tool"] == "lawdocx-comments"
    file_entry = payload["files"][0]
    assert file_entry["path"] == str(path)
    assert file_entry["sha256"]
    assert any(item["type"] == "comment" for item in file_entry["items"])
