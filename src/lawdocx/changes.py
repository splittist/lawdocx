"""Extract tracked changes from DOCX files."""
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

TRACKED_TAGS = {
    "ins": "insertion",
    "del": "deletion",
    "moveFrom": "move_from",
    "moveTo": "move_to",
}


def _base_location(story: str, paragraph_index: int) -> dict:
    return {
        "story": story,
        "paragraph_index_start": paragraph_index,
        "paragraph_index_end": paragraph_index,
    }


def _error_finding(message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="insertion",
        severity="error",
        location=_base_location("body", 0),
        context={"before": "", "target": "", "after": ""},
        details={"category": "error", "message": message},
    )


def _extract_text(node: etree._Element) -> str:
    texts: list[str] = []
    for tag in ("t", "delText"):
        for text_node in node.findall(f".//w:{tag}", namespaces=NS):
            if text_node.text:
                texts.append(text_node.text)
    return "".join(texts)


def _paragraph_changes(paragraph: etree._Element) -> tuple[str, list[dict]]:
    parts: list[str] = []
    changes: list[dict] = []
    current_length = 0

    def _walk(node: etree._Element) -> None:
        nonlocal current_length
        local_name = etree.QName(node).localname

        if local_name in TRACKED_TAGS:
            change_text = _extract_text(node)
            start = current_length
            parts.append(change_text)
            current_length += len(change_text)
            changes.append(
                {
                    "type": TRACKED_TAGS[local_name],
                    "start": start,
                    "end": current_length,
                    "text": change_text,
                    "author": node.get(f"{{{WORD_NAMESPACE}}}author"),
                    "date": node.get(f"{{{WORD_NAMESPACE}}}date"),
                }
            )
            return

        if local_name in {"t", "delText"}:
            value = node.text or ""
            parts.append(value)
            current_length += len(value)
            return

        for child in node:
            _walk(child)

    _walk(paragraph)
    return "".join(parts), changes


def _change_details(change: dict) -> dict:
    text_field = (
        "inserted_text"
        if change["type"] in {"insertion", "move_to"}
        else "deleted_text"
    )
    details = {text_field: change["text"]}
    if change.get("author"):
        details["author"] = change["author"]
    if change.get("date"):
        details["date"] = change["date"]
    return details


def _collect_story_changes(
    xml_bytes: bytes,
    story: str,
    findings: list[Finding],
) -> None:
    root = etree.fromstring(xml_bytes)
    paragraphs = root.findall(".//w:p", namespaces=NS)

    for para_index, paragraph in enumerate(paragraphs):
        paragraph_text, change_records = _paragraph_changes(paragraph)
        for change in change_records:
            findings.append(
                    Finding(
                        id=uuid4().hex[:8],
                        type=change["type"],
                        severity="warning",
                        location=_base_location(story, para_index),
                        context=text_context(paragraph_text, change["start"], change["end"]),
                        details=_change_details(change),
                    )
            )


def _collect_notes_changes(
    xml_bytes: bytes,
    story: str,
    note_tag: str,
    findings: list[Finding],
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
            paragraph_text, change_records = _paragraph_changes(paragraph)
            for change in change_records:
                findings.append(
                    Finding(
                        id=uuid4().hex[:8],
                        type=change["type"],
                        severity="warning",
                        location=_base_location(story, paragraph_index),
                        context=text_context(paragraph_text, change["start"], change["end"]),
                        details=_change_details(change),
                    )
                )
            paragraph_index += 1


def collect_changes(file_path: str) -> list[Finding]:
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
        return [_error_finding(f"Failed to open DOCX: {exc}")]

    try:
        _collect_story_changes(
            document_xml, "body", findings
        )
        for name in sorted(header_parts):
            _collect_story_changes(header_parts[name], "header", findings)
        for name in sorted(footer_parts):
            _collect_story_changes(footer_parts[name], "footer", findings)
        if footnotes_xml:
            _collect_notes_changes(footnotes_xml, "footnote", "footnote", findings)
        if endnotes_xml:
            _collect_notes_changes(endnotes_xml, "endnote", "endnote", findings)
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(f"Change extraction failed: {exc}"))

    return findings


def run_changes(inputs: Iterable[InputSource]) -> dict:
    generated_at = utc_timestamp()
    merged_files: List[dict] = []

    for source in inputs:
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

        findings = collect_changes(target_path)

        file_entry = {
            "path": source.display_name,
            "sha256": sha256,
            "items": [f.as_dict() for f in findings],
        }

        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

        merged_files.append(file_entry)

    return build_envelope(
        tool="lawdocx-changes", files=merged_files, generated_at=generated_at
    )
