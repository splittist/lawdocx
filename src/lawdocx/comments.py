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


def _base_location(comment_index: int, file_index: int | None, comment_id: str | None) -> dict:
    location = {
        "story": "comment",
        "paragraph_index_start": comment_index,
        "paragraph_index_end": comment_index,
    }
    if file_index is not None:
        location["file_index"] = file_index
    if comment_id is not None:
        location["comment_id"] = comment_id
    return location


def _error_finding(file_index: int | None, message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="comment",
        severity="error",
        location=_base_location(0, file_index, None),
        context={"before": "", "target": "", "after": ""},
        details={"category": "error", "message": message},
    )


def _paragraph_text(paragraph: etree._Element) -> str:
    texts: list[str] = []
    for text_node in paragraph.findall(".//w:t", namespaces=NS):
        if text_node.text:
            texts.append(text_node.text)
    return "".join(texts)


def _comment_text(comment_elem: etree._Element) -> tuple[str, str | None]:
    paragraphs = comment_elem.findall(".//w:p", namespaces=NS)
    para_texts: list[str] = []
    last_para_id: str | None = None

    for paragraph in paragraphs:
        para_texts.append(_paragraph_text(paragraph))
        last_para_id = paragraph.get(f"{{{W14_NAMESPACE}}}paraId", last_para_id)

    return "\n".join(para_texts), last_para_id


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


def collect_comments(
    file_path: str, file_index: int | None = None, location_path: str | None = None
) -> list[Finding]:
    findings: list[Finding] = []
    location_path = location_path or file_path

    try:
        with zipfile.ZipFile(file_path) as zf:
            try:
                comments_xml = zf.read("word/comments.xml")
            except KeyError:
                return findings

            extended_map = _parse_comments_extended(zf)
    except Exception as exc:  # pragma: no cover - defensive
        return [_error_finding(file_index, f"Failed to open DOCX: {exc}")]

    try:
        root = etree.fromstring(comments_xml)
        para_to_comment_id: dict[str, str] = {}

        comments = root.findall(".//w:comment", namespaces=NS)
        for index, comment in enumerate(comments):
            comment_id = comment.get(f"{{{WORD_NAMESPACE}}}id")
            author = comment.get(f"{{{WORD_NAMESPACE}}}author")
            date = comment.get(f"{{{WORD_NAMESPACE}}}date")
            comment_text, last_para_id = _comment_text(comment)

            if last_para_id and comment_id:
                para_to_comment_id[last_para_id] = comment_id

            extended = extended_map.get(last_para_id or "", {})
            resolved = bool(extended.get("done")) if extended.get("done") is not None else False
            parent_comment_id = None
            parent_para_id = extended.get("parent_para_id")
            if parent_para_id:
                parent_comment_id = para_to_comment_id.get(parent_para_id)

            details = {"resolved": resolved}
            if author:
                details["author"] = author
            if date:
                details["date"] = date
            if parent_comment_id:
                details["parent_comment_id"] = parent_comment_id

            findings.append(
                Finding(
                    id=uuid4().hex[:8],
                    type="comment",
                    severity="info",
                    location={
                        **_base_location(index, file_index, comment_id),
                        "file_path": location_path,
                    },
                    context=text_context(comment_text, 0, len(comment_text)),
                    details=details,
                )
            )
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(
            _error_finding(file_index, f"Comment extraction failed: {exc}")
        )

    return findings


def run_comments(inputs: Iterable[InputSource], merge: bool, output_handle) -> None:
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

        findings = collect_comments(
            target_path, file_index if merge else None, location_path=source.display_name
        )

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
                tool="lawdocx-comments", files=[file_entry], generated_at=generated_at
            )
            dump_json_line(envelope, output_handle)

    if merge:
        envelope = build_envelope(
            tool="lawdocx-comments", files=merged_files, generated_at=generated_at
        )
        dump_json_line(envelope, output_handle)

