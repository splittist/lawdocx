"""Extract footnotes and endnotes from DOCX files."""
from __future__ import annotations

import zipfile
from pathlib import Path, PurePosixPath
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
RELATIONSHIP_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL_NAMESPACE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": WORD_NAMESPACE}


def _base_location(story: str, paragraph_index: int) -> dict:
    return {
        "story": story,
        "paragraph_index_start": paragraph_index,
        "paragraph_index_end": paragraph_index,
    }


def _error_finding(file_index: int, message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="footnote",
        severity="error",
        location=_base_location("main", 0),
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


def _load_notes_from_bytes(xml_bytes: bytes | None, note_tag: str) -> dict[int, str]:
    if not xml_bytes:
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


def _load_notes(zipf: zipfile.ZipFile, filename: str, note_tag: str) -> dict[int, str]:
    try:
        xml_bytes = zipf.read(filename)
    except KeyError:
        return {}

    return _load_notes_from_bytes(xml_bytes, note_tag)


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


def _relationship_targets(zipf: zipfile.ZipFile, rels_path: str) -> dict[str, str]:
    try:
        rels_xml = zipf.read(rels_path)
    except KeyError:
        return {}

    root = etree.fromstring(rels_xml)
    targets: dict[str, str] = {}

    for rel in root.findall(f".//{{{RELATIONSHIP_NAMESPACE}}}Relationship"):
        rid = rel.get("Id")
        target = rel.get("Target")
        if rid and target:
            targets[rid] = target

    return targets


def _resolve_target(base_part: str, target: str) -> str:
    base_dir = PurePosixPath(base_part).parent
    return base_dir.joinpath(PurePosixPath(target)).as_posix()


def _iter_note_stories(xml_bytes: bytes | None, note_tag: str) -> list[tuple[str, list[etree._Element]]]:
    if not xml_bytes:
        return []

    root = etree.fromstring(xml_bytes)
    stories: list[tuple[str, list[etree._Element]]] = []

    for note in root.findall(f".//w:{note_tag}", namespaces=NS):
        note_id = note.get(f"{{{WORD_NAMESPACE}}}id")
        try:
            parsed_id = int(note_id) if note_id is not None else None
        except ValueError:
            parsed_id = None
        if parsed_id is None or parsed_id <= 0:
            continue

        paragraphs = note.findall(".//w:p", namespaces=NS)
        stories.append((f"{note_tag}--{parsed_id}", paragraphs))

    return stories


def _header_footer_stories(
    document_root: etree._Element, rels_map: dict[str, str], zipf: zipfile.ZipFile
) -> list[tuple[str, list[etree._Element]]]:
    stories: list[tuple[str, list[etree._Element]]] = []
    sect_prs = document_root.findall(".//w:sectPr", namespaces=NS)

    for section_index, sect in enumerate(sect_prs, start=1):
        for ref_tag, prefix in (("headerReference", "header"), ("footerReference", "footer")):
            for ref in sect.findall(f"w:{ref_tag}", namespaces=NS):
                rel_id = ref.get(f"{{{OFFICE_REL_NAMESPACE}}}id")
                target = rels_map.get(rel_id) if rel_id else None
                if not target:
                    continue

                ref_type = ref.get(f"{{{WORD_NAMESPACE}}}type", "default")
                part_path = _resolve_target("word/document.xml", target)

                try:
                    part_xml = zipf.read(part_path)
                except KeyError:
                    continue

                try:
                    part_root = etree.fromstring(part_xml)
                except etree.XMLSyntaxError:
                    continue

                paragraphs = part_root.findall(".//w:p", namespaces=NS)
                story_name = f"{prefix}--Section{section_index}--{ref_type}"
                stories.append((story_name, paragraphs))

    return stories


def collect_footnotes(file_path: str, file_index: int = 0) -> list[Finding]:
    findings: list[Finding] = []

    try:
        with zipfile.ZipFile(file_path) as zf:
            document_xml = zf.read("word/document.xml")
            rels_map = _relationship_targets(zf, "word/_rels/document.xml.rels")
            footnotes_xml = (
                zf.read("word/footnotes.xml") if "word/footnotes.xml" in zf.namelist() else None
            )
            endnotes_xml = (
                zf.read("word/endnotes.xml") if "word/endnotes.xml" in zf.namelist() else None
            )
            footnotes = _load_notes_from_bytes(footnotes_xml, "footnote")
            endnotes = _load_notes_from_bytes(endnotes_xml, "endnote")

            document_root = etree.fromstring(document_xml)
            stories: list[tuple[str, list[etree._Element]]] = []

            body_paragraphs = document_root.findall(".//w:body//w:p", namespaces=NS)
            stories.append(("main", body_paragraphs))

            stories.extend(_header_footer_stories(document_root, rels_map, zf))
            stories.extend(_iter_note_stories(footnotes_xml, "footnote"))
            stories.extend(_iter_note_stories(endnotes_xml, "endnote"))

            for story, paragraphs in stories:
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
                                location=_base_location(story, para_index),
                                context=text_context(paragraph_text, ref["start"], ref["end"]),
                                details=details,
                            )
                        )
    except Exception as exc:  # pragma: no cover - defensive
        return [_error_finding(file_index, f"Failed to open DOCX: {exc}")]

    return findings


def run_footnotes(inputs: Iterable[InputSource]) -> dict:
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

        findings = collect_footnotes(target_path, file_index)

        file_entry = {
            "path": source.display_name,
            "sha256": sha256,
            "items": [f.as_dict() for f in findings],
        }

        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

        merged_files.append(file_entry)

    return build_envelope(
        tool="lawdocx-footnotes", files=merged_files, generated_at=generated_at
    )
