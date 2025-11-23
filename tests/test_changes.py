import json

from lawdocx.changes import collect_changes
from tests.docx_factory import create_changes_docx


def test_collect_changes_across_stories(tmp_path):
    path = create_changes_docx(tmp_path, "changes.docx")

    findings = collect_changes(str(path))

    assert {f.type for f in findings} == {
        "insertion",
        "deletion",
        "move_from",
        "move_to",
    }

    stories = {f.location["story"] for f in findings}
    assert stories == {"body", "header", "footer", "footnote", "endnote"}

    body_change = next(f for f in findings if f.location["story"] == "body")
    assert body_change.details["inserted_text"] == "inserted"
    assert body_change.details["author"] == "Alice"

    deletion = next(f for f in findings if f.type == "deletion")
    assert deletion.details["deleted_text"] == "Header change"

    assert all("file_path" not in f.location for f in findings)
    assert all("file_index" not in f.location for f in findings)

    serialized = [finding.as_dict() for finding in findings]
    assert json.loads(json.dumps(serialized))
