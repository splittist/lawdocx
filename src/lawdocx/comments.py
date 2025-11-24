"""Extract comments (including modern threading and resolved state) from DOCX files."""
from __future__ import annotations

import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, List
from uuid import uuid4

from lxml import etree

from lawdocx.io_utils import InputSource
from lawdocx.models import Finding
from lawdocx.utils import build_envelope, dump_json_line, hash_bytes, text_context, utc_timestamp

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14_NAMESPACE = "http://schemas.microsoft.com/office/word/2010/wordml"
W15_NAMESPACE = "http://schemas.microsoft.com/office/word/2012/wordml"

NS = {
    "w": WORD_NAMESPACE,
    "w14": W14_NAMESPACE,
    "w15": W15_NAMESPACE,
}


def _base_location(
    paragraph_start: int,
    paragraph_end: int,
    comment_id: str | None,
) -> dict:
    location = {
        "story": "comment",
        "paragraph_index_start": paragraph_start,
        "paragraph_index_end": paragraph_end,
    }
    if comment_id is not None:
        location["comment_id"] = comment_id
    return location


def _error_finding(message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="comment",
        severity="error",
        location=_base_location(0, 0, None),
        context={"before": "", "target": "", "after": ""},
        details={"category": "error", "message": message},
    )


def _paragraph_text(paragraph: etree._Element) -> str:
    texts: list[str] = []
    for text_node in paragraph.findall(".//w:t", namespaces=NS):
        if text_node.text:
            texts.append(text_node.text)
    return "".join(texts)


def _comment_paragraphs(comment_elem: etree._Element) -> tuple[list[str], list[str]]:
    paragraphs = comment_elem.findall(".//w:p", namespaces=NS)
    para_texts: list[str] = []
    para_ids: list[str] = []

    for paragraph in paragraphs:
        para_texts.append(_paragraph_text(paragraph))
        para_id = paragraph.get(f"{{{W14_NAMESPACE}}}paraId")
        if para_id:
            para_ids.append(para_id)

    return para_texts, para_ids


def _scan_body_comment_ranges(document_xml: bytes) -> tuple[str, dict[str, dict[str, int]]]:
    root = etree.fromstring(document_xml)
    text_parts: list[str] = []
    open_ranges: dict[str, int] = {}
    ranges: dict[str, dict[str, int]] = {}
    current_length = 0

    def _walk(node: etree._Element) -> None:
        nonlocal current_length
        local_name = etree.QName(node).localname

        if local_name in {"commentRangeStart", "commentRangeEnd"}:
            comment_id = node.get(f"{{{WORD_NAMESPACE}}}id")
            if comment_id:
                if local_name == "commentRangeStart":
                    open_ranges[comment_id] = current_length
                else:
                    start = open_ranges.pop(comment_id, None)
                    if start is not None:
                        ranges[comment_id] = {"start": start, "end": current_length}

        if local_name in {"t", "delText"}:
            value = node.text or ""
            text_parts.append(value)
            current_length += len(value)

        for child in node:
            _walk(child)

    _walk(root)
    return "".join(text_parts), ranges


def _parse_comments_extended(zipf: zipfile.ZipFile) -> dict[str, dict]:
    try:
        raw = zipf.read("word/commentsExtended.xml")
    except KeyError:
        return {}

    root = etree.fromstring(raw)
    extended: dict[str, dict] = {}

    for comment_ex in root.findall(".//w15:commentEx", namespaces=NS):
        para_id = comment_ex.get(f"{{{W15_NAMESPACE}}}paraId")
        if not para_id:
            continue
        done_attr = comment_ex.get(f"{{{W15_NAMESPACE}}}done")
        parent_para_id = comment_ex.get(f"{{{W15_NAMESPACE}}}paraIdParent")

        extended[para_id] = {
            "done": done_attr.lower() in {"1", "true"} if done_attr else None,
            "parent_para_id": parent_para_id,
        }

    return extended


def collect_comments(file_path: str) -> list[Finding]:
    findings: list[Finding] = []

    try:
        with zipfile.ZipFile(file_path) as zf:
            try:
                comments_xml = zf.read("word/comments.xml")
            except KeyError:
                return findings

            try:
                document_xml = zf.read("word/document.xml")
                body_text, range_map = _scan_body_comment_ranges(document_xml)
            except Exception:
                body_text = ""
                range_map = {}

            extended_map = _parse_comments_extended(zf)
    except Exception as exc:  # pragma: no cover - defensive
        return [_error_finding(f"Failed to open DOCX: {exc}")]

    try:
        root = etree.fromstring(comments_xml)
        para_to_comment_id: dict[str, str] = {}

        comments = root.findall(".//w:comment", namespaces=NS)
        for comment in comments:
            comment_id = comment.get(f"{{{WORD_NAMESPACE}}}id")
            author = comment.get(f"{{{WORD_NAMESPACE}}}author")
            date = comment.get(f"{{{WORD_NAMESPACE}}}date")
            comment_paragraphs, para_ids = _comment_paragraphs(comment)
            comment_text = "\n".join(comment_paragraphs)
            paragraph_start = 0 if comment_paragraphs else 0
            paragraph_end = len(comment_paragraphs) - 1 if comment_paragraphs else 0

            for para_id in para_ids:
                if comment_id:
                    para_to_comment_id[para_id] = comment_id

            extended = next((extended_map[id_] for id_ in para_ids if id_ in extended_map), {})
            resolved = bool(extended.get("done")) if extended.get("done") is not None else False
            parent_comment_id = None
            parent_para_id = extended.get("parent_para_id")
            if parent_para_id:
                parent_comment_id = para_to_comment_id.get(parent_para_id)

            details = {"resolved": resolved, "comment_text": comment_text}
            if author:
                details["author"] = author
            initials = comment.get(f"{{{WORD_NAMESPACE}}}initials")
            if initials:
                details["initials"] = initials
            if date:
                details["date"] = date
            if parent_comment_id:
                details["parent_comment_id"] = parent_comment_id

            if comment_id and comment_id in range_map and body_text:
                span = range_map[comment_id]
                context = text_context(body_text, span["start"], span["end"])
            else:
                context = text_context(comment_text, 0, len(comment_text))

            findings.append(
                Finding(
                    id=uuid4().hex[:8],
                    type="comment",
                    severity="info",
                    location={
                        **_base_location(paragraph_start, paragraph_end, comment_id),
                    },
                    context=context,
                    details=details,
                )
            )
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(f"Comment extraction failed: {exc}"))

    return findings


def run_comments(inputs: Iterable[InputSource]) -> dict:
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

        findings = collect_comments(target_path)

        file_entry = {
            "path": source.display_name,
            "sha256": sha256,
            "items": [f.as_dict() for f in findings],
        }

        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

        merged_files.append(file_entry)

    return build_envelope(
        tool="lawdocx-comments", files=merged_files, generated_at=generated_at
    )

