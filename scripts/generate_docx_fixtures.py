"""Generate persistent DOCX fixtures for development and new tests.

This script mirrors the factory helpers in ``tests.docx_factory`` and writes
sample DOCX files into ``tests/fixtures``. It is intended to be run manually
when fresh fixtures are needed (for example, before writing regression tests
that rely on static documents).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

# Ensure the repository root (which contains the ``tests`` package) is on the
# import path when the script is executed directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.docx_factory import (
    create_boilerplate_docx,
    create_changes_docx,
    create_comments_docx,
    create_highlights_docx,
    create_metadata_docx,
    create_multistory_notes_docx,
    create_notes_docx,
    create_outline_docx,
)


@dataclass
class Fixture:
    """A single fixture definition."""

    name: str
    builder: Callable[[Path, str], Path]
    kwargs: dict


FIXTURE_GROUPS: dict[str, Iterable[Fixture]] = {
    "metadata": [
        Fixture(
            name="metadata_sample.docx",
            builder=create_metadata_docx,
            kwargs={"include_custom": True},
        ),
        Fixture(
            name="metadata_no_custom.docx",
            builder=create_metadata_docx,
            kwargs={"include_custom": False, "include_custom_xml": False},
        ),
    ],
    "boilerplate": [
        Fixture(
            name="audit.docx",
            builder=create_boilerplate_docx,
            kwargs={"header_text": "TODO item", "body_paragraphs": ["Simple body"]},
        ),
        Fixture(
            name="audit_only.docx",
            builder=create_boilerplate_docx,
            kwargs={},
        ),
        Fixture(
            name="audit_fail.docx",
            builder=create_boilerplate_docx,
            kwargs={"header_text": "TODO this"},
        ),
        Fixture(
            name="boilerplate.docx",
            builder=create_boilerplate_docx,
            kwargs={
                "header_text": "DRAFT for discussion only",
                "footer_text": "© 2025 Davis Polk & Wardwell LLP",
                "body_paragraphs": ["Agreement dated ________", "Page 1 of 3"],
            },
        ),
        Fixture(
            name="sectioned.docx",
            builder=create_boilerplate_docx,
            kwargs={
                "header_text": "DRAFT for discussion only",
                "footer_text": "© 2025 Davis Polk & Wardwell LLP",
            },
        ),
        Fixture(
            name="custom.docx",
            builder=create_boilerplate_docx,
            kwargs={"header_text": "SAFE HARBOR NOTICE"},
        ),
        Fixture(
            name="cli-brackets.docx",
            builder=create_boilerplate_docx,
            kwargs={
                "header_text": "[Header check]",
                "footer_text": "Footer text",
                "body_paragraphs": ["Body [content]"],
            },
        ),
        Fixture(
            name="stdin-one.docx",
            builder=create_boilerplate_docx,
            kwargs={"header_text": "Draft only"},
        ),
        Fixture(
            name="stdin-two.docx",
            builder=create_boilerplate_docx,
            kwargs={"footer_text": "Page 3 of 5"},
        ),
        Fixture(
            name="todos.docx",
            builder=create_boilerplate_docx,
            kwargs={
                "header_text": "TODO header",
                "footer_text": "Footer [TBD]",
                "body_paragraphs": ["Body needs CHECK"],
            },
        ),
        Fixture(
            name="dedupe.docx",
            builder=create_boilerplate_docx,
            kwargs={"header_text": "TODO item"},
        ),
        Fixture(
            name="boilerplate-envelope.docx",
            builder=create_boilerplate_docx,
            kwargs={
                "header_text": "For discussion only",
                "footer_text": "© 2024 Example LLP",
                "body_paragraphs": ["Dated ________"],
            },
        ),
        Fixture(
            name="todos-envelope.docx",
            builder=create_boilerplate_docx,
            kwargs={"footer_text": "[confirm with client]"},
        ),
        Fixture(
            name="brackets.docx",
            builder=create_boilerplate_docx,
            kwargs={
                "header_text": "[Header note]",
                "footer_text": "[Footer text]",
                "body_paragraphs": ["Body with [outer [inner] brackets] present."],
            },
        ),
        Fixture(
            name="multiline.docx",
            builder=create_boilerplate_docx,
            kwargs={
                "header_text": "",
                "footer_text": "",
                "body_paragraphs": ["First line", "continues on the next"],
            },
        ),
        Fixture(
            name="severity.docx",
            builder=create_boilerplate_docx,
            kwargs={"body_paragraphs": ["Please [review] this clause"]},
        ),
    ],
    "outline": [
        Fixture(
            name="outline.docx",
            builder=create_outline_docx,
            kwargs={},
        ),
        Fixture(
            name="outline-envelope.docx",
            builder=create_outline_docx,
            kwargs={},
        ),
    ],
    "notes": [
        Fixture(
            name="notes.docx",
            builder=create_notes_docx,
            kwargs={},
        ),
        Fixture(
            name="notes-alt.docx",
            builder=create_notes_docx,
            kwargs={"footnote_text": "Alt footnote", "endnote_text": "Endnote text"},
        ),
        Fixture(
            name="notes-brackets.docx",
            builder=create_notes_docx,
            kwargs={
                "footnote_text": "Footnote [text] here",
                "endnote_text": "Endnote [value]",
            },
        ),
        Fixture(
            name="notes-envelope.docx",
            builder=create_notes_docx,
            kwargs={},
        ),
        Fixture(
            name="multi-story-notes.docx",
            builder=create_multistory_notes_docx,
            kwargs={},
        ),
    ],
    "comments": [
        Fixture(
            name="comments.docx",
            builder=create_comments_docx,
            kwargs={},
        ),
    ],
    "changes": [
        Fixture(
            name="changes.docx",
            builder=create_changes_docx,
            kwargs={},
        ),
    ],
    "highlights": [
        Fixture(
            name="highlights.docx",
            builder=create_highlights_docx,
            kwargs={},
        ),
        Fixture(
            name="highlights-envelope.docx",
            builder=create_highlights_docx,
            kwargs={},
        ),
    ],
}


def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
    base_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for group_name, fixtures in FIXTURE_GROUPS.items():
        group_dir = base_dir / group_name
        group_dir.mkdir(parents=True, exist_ok=True)

        for fixture in fixtures:
            path = fixture.builder(group_dir, fixture.name, **fixture.kwargs)
            generated.append(path)

    print("Generated fixtures:")
    for path in sorted(generated):
        print(f"- {path.relative_to(base_dir)}")


if __name__ == "__main__":
    main()
