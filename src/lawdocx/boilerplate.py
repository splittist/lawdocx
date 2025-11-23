"""Detect common boilerplate in DOCX headers and footers only."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List
from uuid import uuid4

from docx2python import docx2python

from lawdocx.io_utils import InputSource
from lawdocx.models import Finding
from lawdocx.utils import build_envelope, dump_json_line, hash_bytes, utc_timestamp

DEFAULT_BOILERPLATE = [
    # 1–12: Draft / watermark legends (case-insensitive)
    r"(?i)drafts?.*?(only|purposes|—|$)",
    r"(?i)for discussion.*?(only|purposes)?",
    r"(?i)confidential.*?(draft|discussion)",
    r"(?i)internal.*?(use|only)",
    r"(?i)privileged.*?(confidential|attorney)",
    r"(?i)attorney.*?(work product|client privilege)",
    r"(?i)not for distribution",
    r"(?i)working copy",
    r"(?i)review copy",
    r"(?i)execution.*?(version|copy).*?(draft|missing)",
    r"(?i)draft.*?execution",
    r"(?i)subject to.*?approval",

    # 13–18: Law-firm footers / legends
    r"©?\s*\d{4}\s+[-&'\w\s]+(?:LLP|PC|LLC|P\.A\.?|L\.L\.P\.?)",
    r"Prepared by\s+[-&\w\s]+(?:LLP|PC|Law)",
    r"Confidential\s*[-–—]\s*[-&\w\s]+(?:LLP|LLC|PC)",
    r"©?\s*All Rights Reserved\s*[-&\w\s]+(?:LLP|PC)",
    r"(?i)privileged and confidential",
    r"(?i)attorney[- ]client privilege",

    # 19–25: Page numbering artifacts
    r"Page\s+\d+\s+of\s+\d+",
    r"Page\s+\d+\s*/\s*\d+",
    r"\d+\s+of\s+\d+",
    r"‹#›|{#}|<Page>|\{ PAGE \}|\{ NUMPAGES \}",
    r"-\s*\d+\s*-",
    r"(?i)page\s*\d+",

    # 26–31: Placeholder dates
    r"\[\s*Date\s*\]",
    r"\[?\s*_{5,}\s*\]?",
    r"As of\s*_{3,}|As of\s*,?\s*\d{4}",
    r"Dated\s*[:–]?\s*_{3,}",
    r"\d{4}\s*-\s*\d{2}\s*-\s*\d{2}\s*Draft",
    r"(?i)as of\s+<date>",

    # 32–34: File-path / temporary artifacts
    r"[A-Z]:\\.+\\.docx?",
    r"/Users/.+/",
    r"~\$",
]

def _base_location(file_index: int, story: str, paragraph_index: int) -> dict:
    return {
        "file_index": file_index,
        "story": story,
        "paragraph_index_start": paragraph_index,
        "paragraph_index_end": paragraph_index,
    }


def _context(text: str, start: int, end: int) -> dict:
    return {
        "before": text[max(0, start - 100):start],
        "target": text[start:end][:500],
        "after": text[end:end + 100],
    }


def _error_finding(file_index: int, message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="boilerplate",
        severity="error",
        location=_base_location(file_index, "header", 0),
        context={"before": "", "target": "", "after": ""},
        details={"category": "error", "message": message},
    )

def _flatten(paragraphs: list) -> list[str]:
    """Flatten docx2python's nested paragraph representation into strings."""

    flat: list[str] = []

    def _walk(node):
        if isinstance(node, str):
            flat.append(node)
        elif isinstance(node, list):
            for child in node:
                _walk(child)

    _walk(paragraphs)
    return flat


def collect_boilerplate(
    file_path: str,
    file_index: int = 0,
    *,
    patterns: Iterable[str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    compiled = [re.compile(p) for p in (patterns or DEFAULT_BOILERPLATE)]

    try:
        content = docx2python(file_path, html=False)
    except Exception as exc:
        return [_error_finding(file_index, f"Failed to open DOCX: {exc}")]

    try:
        sections = {
            "header": _flatten(content.header),
            "footer": _flatten(content.footer),
        }

        for story, paragraphs in sections.items():
            for para_index, paragraph in enumerate(paragraphs):
                for pattern in compiled:
                    for match in pattern.finditer(paragraph):
                        findings.append(
                            Finding(
                                id=uuid4().hex[:8],
                                type="boilerplate",
                                severity="warning",
                                location=_base_location(file_index, story, para_index),
                                context=_context(paragraph, match.start(), match.end()),
                                details={"matched_pattern": match.group(0)},
                            )
                        )
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(file_index, f"Boilerplate scan failed: {exc}"))
    finally:
        content.close()

    return findings


def run_boilerplate(inputs: Iterable[InputSource], merge: bool, output_handle) -> None:
    generated_at = utc_timestamp()
    merged_files: List[dict] = []

    for file_index, source in enumerate(inputs):
        data = source.handle.read()
        sha256 = hash_bytes(data)

        temp_path: str | None = None
        if source.is_stdin:
            from tempfile import NamedTemporaryFile

            with NamedTemporaryFile(delete=False, suffix=".docx") as temp:
                temp.write(data)
                temp_path = temp.name
            target_path = temp_path
        else:
            target_path = source.path

        findings = collect_boilerplate(target_path, file_index if merge else 0)

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
                tool="lawdocx-boilerplate",
                files=[file_entry],
                generated_at=generated_at,
            )
            dump_json_line(envelope, output_handle)

    if merge:
        envelope = build_envelope(
            tool="lawdocx-boilerplate",
            files=merged_files,
            generated_at=generated_at,
        )
        dump_json_line(envelope, output_handle)
