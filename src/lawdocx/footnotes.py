"""Extract footnotes and endnotes from DOCX files."""
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
    dump_json_line,
    hash_bytes,
    text_context,
    utc_timestamp,
)

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WORD_NAMESPACE}


def _base_location(paragraph_index: int, file_index: int) -> dict:
    return {
        "file_index": file_index,
        "story": "body",
        "paragraph_index_start": paragraph_index,
        "paragraph_index_end": paragraph_index,
    }


def _error_finding(file_index: int, message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="footnote",
        severity="error",
        location=_base_location(0, file_index),
        context={"before": "", "target": "", "after": ""},
        details={"category": "error", "message": message},
    )


def _note_text(note_elem: etree._Element) -> str:
    paragraphs = note_elem.findall(".//w:p", namespaces=NS)
    if not paragraphs:
        return ""

    def _paragraph_text(paragraph: etree._Element) -> str:
        texts = []
        for text_node in paragraph.findall(".//w:t", namespaces=NS):
            if text_node.text:
                texts.append(text_node.text)
        return "".join(texts)

    return "\n".join(_paragraph_text(paragraph) for paragraph in paragraphs)


def _load_notes(zipf: zipfile.ZipFile, filename: str, note_tag: str) -> dict[int, str]:
    try:
        xml_bytes = zipf.read(filename)
    except KeyError:
        return {}

    root = etree.fromstring(xml_bytes)
    notes: dict[int, str] = {}

    for note in root.findall(f".//w:{note_tag}", namespaces=NS):
        note_id = note.get(f"{{{WORD_NAMESPACE}}}id")
        if note_id is None:
            continue
        try:
            parsed_id = int(note_id)
        except ValueError:
            continue
        if parsed_id <= 0:
            continue
        notes[parsed_id] = _note_text(note)

    return notes


def _paragraph_text_and_refs(paragraph: etree._Element) -> tuple[str, list[dict]]:
    text_parts: list[str] = []
    refs: list[dict] = []
    current_length = 0

    for node in paragraph.iter():
        tag = etree.QName(node).localname
        if tag == "t":
            value = node.text or ""
            text_parts.append(value)
            current_length += len(value)
        elif tag in {"footnoteReference", "endnoteReference"}:
            note_id = node.get(f"{{{WORD_NAMESPACE}}}id")
            try:
                parsed_id = int(note_id) if note_id is not None else None
            except ValueError:
                parsed_id = None

            placeholder = (
                f"[FN {parsed_id}]" if tag == "footnoteReference" else f"[EN {parsed_id}]"
            )
            start, end = current_length, current_length + len(placeholder)
            text_parts.append(placeholder)
            current_length = end
            refs.append(
                {
                    "type": "footnote" if tag == "footnoteReference" else "endnote",
                    "id": parsed_id,
                    "start": start,
                    "end": end,
                }
            )

    return "".join(text_parts), refs


def collect_footnotes(file_path: str, file_index: int = 0) -> list[Finding]:
    findings: list[Finding] = []

    try:
        with zipfile.ZipFile(file_path) as zf:
            document_xml = zf.read("word/document.xml")
            footnotes = _load_notes(zf, "word/footnotes.xml", "footnote")
            endnotes = _load_notes(zf, "word/endnotes.xml", "endnote")
    except Exception as exc:  # pragma: no cover - defensive
        return [_error_finding(file_index, f"Failed to open DOCX: {exc}")]

    try:
        document_root = etree.fromstring(document_xml)
        paragraphs = document_root.findall(".//w:body//w:p", namespaces=NS)

        for para_index, paragraph in enumerate(paragraphs):
            paragraph_text, references = _paragraph_text_and_refs(paragraph)

            for ref in references:
                note_map = footnotes if ref["type"] == "footnote" else endnotes
                note_text = note_map.get(ref["id"], "") if ref["id"] is not None else ""
                details = {
                    "note_type": ref["type"],
                    "note_id": ref["id"],
                    "note_text": note_text,
                }
                if not note_text:
                    details["status"] = "missing note text"

                findings.append(
                    Finding(
                        id=uuid4().hex[:8],
                        type=ref["type"],
                        severity="info",
                        location=_base_location(para_index, file_index),
                        context=text_context(paragraph_text, ref["start"], ref["end"]),
                        details=details,
                    )
                )
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(file_index, f"Footnote extraction failed: {exc}"))

    return findings


def run_footnotes(inputs: Iterable[InputSource], merge: bool, output_handle) -> None:
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

        findings = collect_footnotes(target_path, file_index if merge else 0)

        file_entry = {
            "path": source.display_name,
            "sha256": sha256,
            "items": [f.as_dict() for f in findings],
        }

        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

        if merge:
            merged_files.append(file_entry)
        else:
            envelope = build_envelope(
                tool="lawdocx-footnotes", files=[file_entry], generated_at=generated_at
            )
            dump_json_line(envelope, output_handle)

    if merge:
        envelope = build_envelope(
            tool="lawdocx-footnotes", files=merged_files, generated_at=generated_at
        )
        dump_json_line(envelope, output_handle)
