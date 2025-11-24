"""Detect TODO- and placeholder-style markers in DOCX files."""
from __future__ import annotations

import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, List
from uuid import uuid4

from docx2python import docx2python

from lawdocx.io_utils import InputSource
from lawdocx.models import Finding
from lawdocx.utils import (
    build_envelope,
    hash_bytes,
    text_context,
    utc_timestamp,
)

DEFAULT_TODO_PATTERNS = [
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bNTD\b",
    r"\bTBD\b",
    r"\bTBC\b",
    r"\bTBA\b",
    r"\bCHECK\b",
    r"\bREVIEW\b",
    r"\bREVISIT\b",
    r"\bCONFIRM\b",
    r"\bVERIFY\b",
    r"\bINSERT\b",
    r"\bDELETE\b",
    r"\bREPLACE\b",
    r"\bREWORD\b",
    r"\bUPDATE\b",
    r"\[\s*\?\s*\]",
    r"\[\s*NTD\s*\]",
    r"\[\s*TODO\s*\]",
    r"\[\s*TBD\s*\]",
    r"\[\s*CHECK\s*\]",
    r"\[\s*REVIEW\s*\]",
    r"\[\s*DISCUSS\s*\]",
    r"\[\s*to be (confirmed|discussed|updated|inserted|deleted|reviewed)\s*\]",
    r"\[\s*client to confirm\s*\]",
    r"\[\s*confirm with client\s*\]",
    r"\[\s*insert (date|amount|name|governing law)\s*\]",
    r"\[\s*delete if not applicable\s*\]",
]


def _base_location(story: str, paragraph_index: int) -> dict:
    return {
        "story": story,
        "paragraph_index_start": paragraph_index,
        "paragraph_index_end": paragraph_index,
    }


def _error_finding(file_index: int, message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="todo",
        severity="error",
        location=_base_location("body", 0),
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
    return [re.compile(pattern) for pattern in unique]


def collect_todos(
    file_path: str,
    file_index: int = 0,
    *,
    patterns: Iterable[str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    compiled = _compile_patterns(patterns or DEFAULT_TODO_PATTERNS)

    try:
        content = docx2python(file_path, html=False)
    except Exception as exc:  # pragma: no cover - defensive
        return [_error_finding(file_index, f"Failed to open DOCX: {exc}")]

    try:
        stories = [
            ("body", _flatten(content.body)),
            ("header", _flatten(content.header)),
            ("footer", _flatten(content.footer)),
        ]

        for story, paragraphs in stories:
            for para_index, paragraph in enumerate(paragraphs):
                for pattern in compiled:
                    for match in pattern.finditer(paragraph):
                        findings.append(
                            Finding(
                                id=uuid4().hex[:8],
                                type="todo",
                                severity="warning",
                                location=_base_location(story, para_index),
                                context=text_context(paragraph, match.start(), match.end()),
                                details={
                                    "matched_pattern": match.group(0),
                                    "raw_text": match.group(0),
                                },
                            )
                        )
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(file_index, f"Todo scan failed: {exc}"))
    finally:
        content.close()

    return findings


def run_todos(inputs: Iterable[InputSource]) -> dict:
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

        findings = collect_todos(target_path, file_index)

        file_entry = {
            "path": source.display_name,
            "sha256": sha256,
            "items": [f.as_dict() for f in findings],
        }

        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

        merged_files.append(file_entry)

    return build_envelope(
        tool="lawdocx-todos", files=merged_files, generated_at=generated_at
    )
