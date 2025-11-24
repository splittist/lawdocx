"""Detect bracketed text spans in DOCX files."""
from __future__ import annotations

import bisect
import re
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, List
from uuid import uuid4

from docx2python import docx2python
from lxml import etree

from lawdocx.io_utils import InputSource
from lawdocx.models import Finding
from lawdocx.utils import build_envelope, hash_bytes, text_context, utc_timestamp

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WORD_NAMESPACE}


def _base_location(story: str, start: int, end: int) -> dict:
    return {
        "story": story,
        "paragraph_index_start": start,
        "paragraph_index_end": end,
    }


def _error_finding(file_index: int, message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="bracket",
        severity="error",
        location=_base_location("body", 0, 0),
        context={"before": "", "target": "", "after": ""},
        details={"category": "error", "message": message},
    )


def _flatten(paragraphs: list) -> list[str]:
    flat: list[str] = []

    def _walk(node):
        if isinstance(node, str):
            flat.append(node)
        elif isinstance(node, list):
            for child in node:
                _walk(child)

    _walk(paragraphs)
    return flat


def _compile_patterns(patterns: Iterable[str]) -> list[re.Pattern[str]]:
    unique = list(dict.fromkeys(patterns))
    return [re.compile(pattern, re.DOTALL | re.MULTILINE) for pattern in unique]


def _build_story_text(paragraphs: list[str]) -> tuple[str, list[int]]:
    starts: list[int] = []
    parts: list[str] = []
    current = 0

    for index, para in enumerate(paragraphs):
        starts.append(current)
        parts.append(para)
        current += len(para)
        if index != len(paragraphs) - 1:
            parts.append("\n")
            current += 1

    return "".join(parts), starts


def _paragraph_index(offset: int, starts: list[int], paragraph_count: int) -> int:
    if not starts:
        return 0
    idx = bisect.bisect_right(starts, offset) - 1
    return max(0, min(idx, paragraph_count - 1))


def _balanced_brackets(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    stack: list[int] = []

    for index, char in enumerate(text):
        if char == "[":
            stack.append(index)
        elif char == "]" and stack:
            start = stack.pop()
            spans.append((start, index + 1))

    spans.sort(key=lambda pair: pair[0])
    return spans


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


def _load_notes(zipf: zipfile.ZipFile, filename: str, tag: str) -> list[str]:
    try:
        xml_bytes = zipf.read(filename)
    except KeyError:
        return []

    root = etree.fromstring(xml_bytes)
    note_entries: list[tuple[int, str]] = []

    for note in root.findall(f".//w:{tag}", namespaces=NS):
        note_id = note.get(f"{{{WORD_NAMESPACE}}}id")
        try:
            parsed_id = int(note_id) if note_id is not None else None
        except ValueError:
            parsed_id = None

        if parsed_id is None or parsed_id <= 0:
            continue

        note_entries.append((parsed_id, _note_text(note)))

    note_entries.sort(key=lambda entry: entry[0])
    return [text for _, text in note_entries]


def _scan_story(
    story: str, paragraphs: list[str], compiled_patterns: list[re.Pattern[str]] | None
) -> list[Finding]:
    findings: list[Finding] = []
    if not paragraphs:
        return findings

    story_text, starts = _build_story_text(paragraphs)
    paragraph_count = len(paragraphs)

    if compiled_patterns:
        matches: list[tuple[int, int, str]] = []
        for pattern in compiled_patterns:
            for match in pattern.finditer(story_text):
                matches.append((match.start(), match.end(), pattern.pattern))
    else:
        matches = [(*span, "default_brackets") for span in _balanced_brackets(story_text)]

    for start, end, pattern in matches:
        para_start = _paragraph_index(start, starts, paragraph_count)
        para_end = _paragraph_index(max(start, end - 1), starts, paragraph_count)
        findings.append(
            Finding(
                id=uuid4().hex[:8],
                type="bracket",
                severity="warning",
                location=_base_location(story, para_start, para_end),
                context=text_context(story_text, start, end),
                details={"matched_pattern": pattern, "raw_text": story_text[start:end]},
            )
        )

    return findings


def collect_brackets(
    file_path: str, file_index: int = 0, *, patterns: Iterable[str] | None = None
) -> list[Finding]:
    findings: list[Finding] = []
    compiled = _compile_patterns(patterns) if patterns else None

    try:
        content = docx2python(file_path, html=False)
    except Exception as exc:  # pragma: no cover - defensive
        return [_error_finding(file_index, f"Failed to open DOCX: {exc}")]

    try:
        stories: list[tuple[str, list[str]]] = [
            ("body", _flatten(content.body)),
            ("header", _flatten(content.header)),
            ("footer", _flatten(content.footer)),
        ]

        try:
            with zipfile.ZipFile(file_path) as zf:
                footnotes = _load_notes(zf, "word/footnotes.xml", "footnote")
                endnotes = _load_notes(zf, "word/endnotes.xml", "endnote")
        except Exception as exc:  # pragma: no cover - defensive
            findings.append(_error_finding(file_index, f"Failed to load notes: {exc}"))
            footnotes = []
            endnotes = []

        if footnotes:
            stories.append(("footnote", footnotes))

        if endnotes:
            stories.append(("endnote", endnotes))

        for story, paragraphs in stories:
            findings.extend(_scan_story(story, paragraphs, compiled))
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(file_index, f"Bracket scan failed: {exc}"))
    finally:
        content.close()

    return findings


def run_brackets(inputs: Iterable[InputSource], *, patterns: Iterable[str] | None) -> dict:
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

        findings = collect_brackets(target_path, file_index, patterns=patterns)

        file_entry = {
            "path": source.display_name,
            "sha256": sha256,
            "items": [f.as_dict() for f in findings],
        }

        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

        merged_files.append(file_entry)

    return build_envelope(
        tool="lawdocx-brackets", files=merged_files, generated_at=generated_at
    )
