"""Detect outline numbering issues in DOCX files."""
from __future__ import annotations

import re
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

MANUAL_NUMBERING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*\d+\.\s"),
    re.compile(r"^\s*\d+\)\s"),
    re.compile(r"^\s*\d+\.[A-Za-z]\s"),
    re.compile(r"^\s*\([A-Za-z]\)\s"),
    re.compile(r"^\s*[ivxlcdm]+\)\s", re.IGNORECASE),
    re.compile(r"^\s*[ivxlcdm]+\.\s", re.IGNORECASE),
]

HEADING_KEYWORDS = ["heading ", "title", "article", "section", "clause", "heading-"]


def _base_location(paragraph_index: int) -> dict:
    return {
        "story": "body",
        "paragraph_index_start": paragraph_index,
        "paragraph_index_end": paragraph_index,
    }


def _error_finding(message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="outline",
        severity="error",
        location=_base_location(0),
        context={"before": "", "target": "", "after": ""},
        details={"category": "error", "message": message},
    )


def _paragraph_text(paragraph: etree._Element) -> str:
    texts: list[str] = []
    for text_node in paragraph.findall(".//w:t", namespaces=NS):
        if text_node.text:
            texts.append(text_node.text)
    return "".join(texts)


def _load_styles(zipf: zipfile.ZipFile) -> dict[str, str]:
    try:
        xml_bytes = zipf.read("word/styles.xml")
    except KeyError:
        return {}

    root = etree.fromstring(xml_bytes)
    styles: dict[str, str] = {}

    for style in root.findall(".//w:style", namespaces=NS):
        style_id = style.get(f"{{{WORD_NAMESPACE}}}styleId")
        name_elem = style.find("w:name", namespaces=NS)
        style_name = name_elem.get(f"{{{WORD_NAMESPACE}}}val") if name_elem is not None else None
        if style_id and style_name:
            styles[style_id] = style_name

    return styles


def _is_heading_style(style_name: str | None) -> bool:
    if not style_name:
        return False
    lowered = style_name.lower()
    return any(keyword in lowered for keyword in HEADING_KEYWORDS)


def _has_manual_numbering(text: str) -> bool:
    return any(pattern.search(text) for pattern in MANUAL_NUMBERING_PATTERNS)


def collect_outline(file_path: str, file_index: int = 0) -> list[Finding]:
    findings: list[Finding] = []

    try:
        with zipfile.ZipFile(file_path) as zf:
            document_xml = zf.read("word/document.xml")
            styles = _load_styles(zf)
    except Exception as exc:  # pragma: no cover - defensive
        return [_error_finding(f"Failed to open DOCX: {exc}")]

    try:
        root = etree.fromstring(document_xml)
        paragraphs = root.findall(".//w:body//w:p", namespaces=NS)

        for para_index, paragraph in enumerate(paragraphs):
            text = _paragraph_text(paragraph)
            style_elem = paragraph.find("./w:pPr/w:pStyle", namespaces=NS)
            style_id = (
                style_elem.get(f"{{{WORD_NAMESPACE}}}val") if style_elem is not None else None
            )
            style_name = styles.get(style_id, style_id or "")

            if _is_heading_style(style_name):
                continue

            has_numpr = paragraph.find("./w:pPr/w:numPr", namespaces=NS) is not None
            manual_numbering = _has_manual_numbering(text)

            if manual_numbering:
                findings.append(
                    Finding(
                        id=uuid4().hex[:8],
                        type="outline",
                        severity="error",
                        location=_base_location(para_index),
                        context=text_context(text, 0, min(len(text), 80), target_limit=80),
                        details={
                            "category": "manual_numbering",
                            "style_name": style_name,
                        },
                    )
                )
            elif has_numpr:
                findings.append(
                    Finding(
                        id=uuid4().hex[:8],
                        type="outline",
                        severity="warning",
                        location=_base_location(para_index),
                        context=text_context(text, 0, min(len(text), 80), target_limit=80),
                        details={
                            "category": "suspicious_numbering",
                            "style_name": style_name,
                        },
                    )
                )
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(f"Outline scan failed: {exc}"))

    return findings


def run_outline(inputs: Iterable[InputSource]) -> dict:
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

        findings = collect_outline(target_path, file_index)

        file_entry = {
            "path": source.display_name,
            "sha256": sha256,
            "items": [f.as_dict() for f in findings],
        }

        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

        merged_files.append(file_entry)

    return build_envelope(
        tool="lawdocx-outline", files=merged_files, generated_at=generated_at
    )
