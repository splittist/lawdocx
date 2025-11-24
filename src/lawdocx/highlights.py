"""Extract text highlighting from DOCX files."""
from __future__ import annotations

import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, List
from uuid import uuid4

from lxml import etree

from lawdocx.io_utils import InputSource
from lawdocx.models import Finding
from lawdocx.utils import (
    build_envelope,
    hash_bytes,
    text_context,
    utc_timestamp,
)

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WORD_NAMESPACE}


def _base_location(story: str, paragraph_index: int) -> dict:
    return {
        "story": story,
        "paragraph_index_start": paragraph_index,
        "paragraph_index_end": paragraph_index,
    }


def _error_finding(message: str, *, file_index: int = 0) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="highlight",
        severity="error",
        location=_base_location("body", 0),
        context={"before": "", "target": "", "after": ""},
        details={"category": "error", "message": message},
    )


def _run_text(run: etree._Element) -> str:
    texts: list[str] = []
    for node in run.findall(".//w:t", namespaces=NS):
        if node.text:
            texts.append(node.text)
    return "".join(texts)


def _paragraph_highlights(paragraph: etree._Element) -> tuple[str, list[dict]]:
    parts: list[str] = []
    highlights: list[dict] = []
    current_length = 0

    for run in paragraph.findall(".//w:r", namespaces=NS):
        run_text = _run_text(run)
        start = current_length
        current_length += len(run_text)
        parts.append(run_text)

        highlight_tag = run.find(".//w:highlight", namespaces=NS)
        if highlight_tag is not None and run_text:
            color = highlight_tag.get(f"{{{WORD_NAMESPACE}}}val") or "yellow"
            highlights.append(
                {
                    "start": start,
                    "end": current_length,
                    "text": run_text,
                    "color": color,
                }
            )

    return "".join(parts), highlights


def _collect_story_highlights(xml_bytes: bytes, story: str, findings: list[Finding]) -> None:
    root = etree.fromstring(xml_bytes)
    paragraphs = root.findall(".//w:p", namespaces=NS)

    for para_index, paragraph in enumerate(paragraphs):
        paragraph_text, highlight_records = _paragraph_highlights(paragraph)
        for record in highlight_records:
            findings.append(
                Finding(
                    id=uuid4().hex[:8],
                    type="highlight",
                    severity="warning",
                    location=_base_location(story, para_index),
                    context=text_context(
                        paragraph_text, record["start"], record["end"]
                    ),
                    details={"highlight_color": record["color"]},
                )
            )


def _collect_notes_highlights(
    xml_bytes: bytes, story: str, note_tag: str, findings: list[Finding]
) -> None:
    root = etree.fromstring(xml_bytes)
    paragraph_index = 0

    for note in root.findall(f".//w:{note_tag}", namespaces=NS):
        note_id = note.get(f"{{{WORD_NAMESPACE}}}id")
        try:
            parsed_id = int(note_id) if note_id is not None else None
        except ValueError:
            parsed_id = None
        if parsed_id is None or parsed_id <= 0:
            continue

        for paragraph in note.findall(".//w:p", namespaces=NS):
            paragraph_text, highlight_records = _paragraph_highlights(paragraph)
            for record in highlight_records:
                findings.append(
                    Finding(
                        id=uuid4().hex[:8],
                        type="highlight",
                        severity="warning",
                        location=_base_location(story, paragraph_index),
                        context=text_context(
                            paragraph_text, record["start"], record["end"]
                        ),
                        details={"highlight_color": record["color"]},
                    )
                )
            paragraph_index += 1


def collect_highlights(file_path: str, file_index: int = 0) -> list[Finding]:
    findings: list[Finding] = []

    try:
        with zipfile.ZipFile(file_path) as zf:
            document_xml = zf.read("word/document.xml")
            header_parts = {
                name: zf.read(name)
                for name in zf.namelist()
                if name.startswith("word/header") and name.endswith(".xml")
            }
            footer_parts = {
                name: zf.read(name)
                for name in zf.namelist()
                if name.startswith("word/footer") and name.endswith(".xml")
            }
            footnotes_xml = (
                zf.read("word/footnotes.xml") if "word/footnotes.xml" in zf.namelist() else None
            )
            endnotes_xml = (
                zf.read("word/endnotes.xml") if "word/endnotes.xml" in zf.namelist() else None
            )
    except Exception as exc:  # pragma: no cover - defensive
        return [_error_finding(f"Failed to open DOCX: {exc}", file_index=file_index)]

    try:
        _collect_story_highlights(document_xml, "body", findings)
        for name in sorted(header_parts):
            _collect_story_highlights(header_parts[name], "header", findings)
        for name in sorted(footer_parts):
            _collect_story_highlights(footer_parts[name], "footer", findings)
        if footnotes_xml:
            _collect_notes_highlights(footnotes_xml, "footnote", "footnote", findings)
        if endnotes_xml:
            _collect_notes_highlights(endnotes_xml, "endnote", "endnote", findings)
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(f"Highlight extraction failed: {exc}", file_index=file_index))

    return findings


def run_highlights(inputs: Iterable[InputSource]) -> dict:
    generated_at = utc_timestamp()
    merged_files: List[dict] = []

    for file_index, source in enumerate(inputs):
        data = source.handle.read()
        sha256 = hash_bytes(data)

        temp_path: str | None = None
        if source.is_stdin:
            with NamedTemporaryFile(delete=False, suffix=".docx") as temp:
                temp.write(data)
                temp_path = temp.name
            target_path = temp_path
        else:
            target_path = source.path

        findings = collect_highlights(target_path, file_index)

        file_entry = {
            "path": source.display_name,
            "sha256": sha256,
            "items": [f.as_dict() for f in findings],
        }

        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

        merged_files.append(file_entry)

    return build_envelope(
        tool="lawdocx-highlights", files=merged_files, generated_at=generated_at
    )
