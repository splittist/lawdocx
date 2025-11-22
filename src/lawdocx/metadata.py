"""Metadata extraction for DOCX files."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from tempfile import NamedTemporaryFile
from typing import Iterable, List
from uuid import uuid4

from docx2python import docx2python
from lxml import etree

from lawdocx import __version__
from lawdocx.io_utils import InputSource


@dataclass
class Finding:
    """Simple representation of a finding object."""

    id: str
    type: str
    severity: str
    location: dict
    context: dict
    details: dict

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "severity": self.severity,
            "location": self.location,
            "context": self.context,
            "details": self.details,
        }


def _base_location(file_index: int) -> dict:
    return {
        "file_index": file_index,
        "story": "metadata",
        "paragraph_index_start": 0,
        "paragraph_index_end": 0,
    }


def _metadata_finding(
    *,
    file_index: int,
    name: str,
    value: str,
    category: str,
    raw_value: str | None = None,
    datatype: str | None = None,
    severity: str = "info",
) -> Finding:
    details = {
        "name": name,
        "category": category,
        "raw_value": raw_value if raw_value is not None else value,
    }
    if datatype:
        details["datatype"] = datatype

    return Finding(
        id=uuid4().hex[:8],
        type="metadata",
        severity=severity,
        location=_base_location(file_index),
        context={"before": "", "target": value, "after": ""},
        details=details,
    )


def _error_finding(file_index: int, message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="metadata",
        severity="error",
        location=_base_location(file_index),
        context={"before": "", "target": "", "after": ""},
        details={"category": "error", "message": message},
    )


def _extract_simple_properties(
    properties: dict[str, str | None], file_index: int, category: str
) -> list[Finding]:
    findings: list[Finding] = []
    for name, value in properties.items():
        value_str = "" if value is None else str(value)
        findings.append(
            _metadata_finding(
                file_index=file_index,
                name=name,
                value=value_str,
                category=category,
                raw_value=value_str,
            )
        )
    return findings


def _extract_extended_properties(files: list, file_index: int) -> list[Finding]:
    findings: list[Finding] = []
    for doc_file in files:
        try:
            for child in doc_file.root_element:
                name = etree.QName(child).localname
                value = child.text or ""
                findings.append(
                    _metadata_finding(
                        file_index=file_index,
                        name=name,
                        value=value,
                        category="extended",
                        raw_value=value,
                    )
                )
        except Exception as exc:  # pragma: no cover - defensive
            findings.append(_error_finding(file_index, f"Extended properties failed: {exc}"))
    return findings


def _extract_custom_properties(files: list, file_index: int) -> list[Finding]:
    findings: list[Finding] = []
    for doc_file in files:
        try:
            for prop in doc_file.root_element.findall(".//{*}property"):
                name = prop.get("name", "")
                if len(prop):
                    value_elem = prop[0]
                    datatype = etree.QName(value_elem).localname
                    value = value_elem.text or ""
                else:
                    datatype = None
                    value = ""
                findings.append(
                    _metadata_finding(
                        file_index=file_index,
                        name=name,
                        value=value,
                        category="custom",
                        raw_value=value,
                        datatype=datatype,
                    )
                )
        except Exception as exc:  # pragma: no cover - defensive
            findings.append(_error_finding(file_index, f"Custom properties failed: {exc}"))
    return findings


def _extract_revision_parts(reader, file_index: int) -> list[Finding]:
    findings: list[Finding] = []
    try:
        revision_files = [
            file for file in reader.files if "revision" in file.path.lower()
        ]
        for rev_file in revision_files:
            raw_bytes = reader.zipf.read(rev_file.path)
            raw_text = raw_bytes.decode("utf-8", errors="replace")
            findings.append(
                _metadata_finding(
                    file_index=file_index,
                    name=rev_file.path,
                    value=raw_text,
                    category="revision",
                    raw_value=raw_text,
                    datatype="xml",
                )
            )
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(file_index, f"Revision history failed: {exc}"))
    return findings


def collect_metadata(file_path: str, file_index: int = 0) -> list[Finding]:
    """Extract metadata from a DOCX file."""

    findings: list[Finding] = []
    try:
        content = docx2python(file_path)
    except Exception as exc:
        return [_error_finding(file_index, f"Failed to open DOCX: {exc}")]

    try:
        findings.extend(
            _extract_simple_properties(content.core_properties, file_index, "core")
        )

        extended_files = content.docx_reader.files_of_type("extended-properties")
        findings.extend(_extract_extended_properties(extended_files, file_index))

        custom_files = content.docx_reader.files_of_type("custom-properties")
        findings.extend(_extract_custom_properties(custom_files, file_index))

        findings.extend(_extract_revision_parts(content.docx_reader, file_index))
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(file_index, f"Metadata extraction failed: {exc}"))
    finally:
        content.close()

    return findings


def _calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _serialize_envelope(envelope: dict, output_handle) -> None:
    json.dump(envelope, output_handle)
    output_handle.write("\n")


def run_metadata(inputs: Iterable[InputSource], merge: bool, output_handle) -> None:
    """Extract metadata for one or more input sources."""

    generated_at = datetime.now(timezone.utc).isoformat()
    merged_files: List[dict] = []

    for file_index, source in enumerate(inputs):
        data = source.handle.read()
        sha256 = _calculate_sha256(data)

        temp_path: str | None = None
        if source.is_stdin:
            with NamedTemporaryFile(delete=False, suffix=".docx") as temp:
                temp.write(data)
                temp_path = temp.name
            target_path = temp_path
        else:
            target_path = source.path

        findings = collect_metadata(target_path, file_index if merge else 0)

        file_entry = {
            "path": source.display_name,
            "sha256": sha256,
            "items": [f.as_dict() for f in findings],
        }

        if temp_path:
            os.unlink(temp_path)

        if merge:
            merged_files.append(file_entry)
        else:
            envelope = {
                "lawdocx_version": __version__,
                "tool": "lawdocx-metadata",
                "generated_at": generated_at,
                "files": [file_entry],
            }
            _serialize_envelope(envelope, output_handle)

    if merge:
        envelope = {
            "lawdocx_version": __version__,
            "tool": "lawdocx-metadata",
            "generated_at": generated_at,
            "files": merged_files,
        }
        _serialize_envelope(envelope, output_handle)
