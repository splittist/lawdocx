"""Metadata extraction for DOCX files."""
from __future__ import annotations

import os
from tempfile import NamedTemporaryFile
from typing import Iterable, List
from uuid import uuid4

from docx2python import docx2python
from lxml import etree

from lawdocx.io_utils import InputSource
from lawdocx.models import Finding
from lawdocx.utils import build_envelope, hash_bytes, utc_timestamp


def _base_location() -> dict:
    return {
        "story": "metadata",
        "paragraph_index_start": 0,
        "paragraph_index_end": 0,
    }


def _metadata_finding(
    *,
    name: str,
    value: str,
    category: str,
    raw_value: str | None = None,
    datatype: str | None = None,
    severity: str = "info",
    extra_details: dict | None = None,
) -> Finding:
    details = {
        "name": name,
        "category": category,
        "raw_value": raw_value if raw_value is not None else value,
    }
    if datatype:
        details["datatype"] = datatype
    if extra_details:
        details.update(extra_details)

    return Finding(
        id=uuid4().hex[:8],
        type="metadata",
        severity=severity,
        location=_base_location(),
        context={"before": "", "target": value, "after": ""},
        details=details,
    )


def _error_finding(message: str) -> Finding:
    return Finding(
        id=uuid4().hex[:8],
        type="metadata",
        severity="error",
        location=_base_location(),
        context={"before": "", "target": "", "after": ""},
        details={"category": "error", "message": message},
    )


def _extract_simple_properties(
    properties: dict[str, str | None], category: str
) -> list[Finding]:
    findings: list[Finding] = []
    for name, value in properties.items():
        value_str = "" if value is None else str(value)
        findings.append(
            _metadata_finding(
                name=name,
                value=value_str,
                category=category,
                raw_value=value_str,
            )
        )
    return findings


def _extract_extended_properties(files: list) -> list[Finding]:
    findings: list[Finding] = []
    for doc_file in files:
        try:
            for child in doc_file.root_element:
                name = etree.QName(child).localname
                value = child.text or ""
                findings.append(
                    _metadata_finding(
                        name=name,
                        value=value,
                        category="extended",
                        raw_value=value,
                    )
                )
        except Exception as exc:  # pragma: no cover - defensive
            findings.append(_error_finding(f"Extended properties failed: {exc}"))
    return findings


def _extract_custom_properties(files: list) -> list[Finding]:
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
                        name=name,
                        value=value,
                        category="custom",
                        raw_value=value,
                        datatype=datatype,
                    )
                )
        except Exception as exc:  # pragma: no cover - defensive
            findings.append(_error_finding(f"Custom properties failed: {exc}"))
    return findings


def _extract_custom_xml_files(reader) -> list[Finding]:
    custom_xml_rel_type = (
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml"
    )
    relationships_path = "word/_rels/document.xml.rels"

    try:
        rels_bytes = reader.zipf.read(relationships_path)
        rels_root = etree.fromstring(rels_bytes)
        custom_paths: list[str] = []

        for rel in rels_root.findall(
            ".//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
        ):
            if rel.get("Type") == custom_xml_rel_type:
                target = rel.get("Target", "").lstrip("/")
                resolved = os.path.normpath(os.path.join("word", target))
                custom_paths.append(resolved)

        unique_paths = sorted(dict.fromkeys(custom_paths))
        count = len(unique_paths)
        summary = f"{count} custom XML part(s) referenced"
        return [
            _metadata_finding(
                name="customXmlParts",
                value=summary,
                category="custom-xml",
                raw_value=summary,
                extra_details={
                    "count": count,
                    "paths": unique_paths,
                },
            )
        ]
    except KeyError:
        return [
            _metadata_finding(
                name="customXmlParts",
                value="0 custom XML part(s) referenced",
                category="custom-xml",
                raw_value="",
                extra_details={"count": 0, "paths": [], "status": "missing document.xml.rels"},
            )
        ]
    except Exception as exc:  # pragma: no cover - defensive
        return [_error_finding(f"Custom XML detection failed: {exc}")]


def collect_metadata(file_path: str) -> list[Finding]:
    """Extract metadata from a DOCX file.

    The ``collect_*`` helpers form the minimal interface for tool modules: they
    accept a path to the working file and return a list of serializable finding
    objects.
    Keeping this surface small helps future tools stay well under the
    150-line-per-module guideline.
    """

    findings: list[Finding] = []
    try:
        content = docx2python(file_path)
    except Exception as exc:
        return [_error_finding(f"Failed to open DOCX: {exc}")]

    try:
        findings.extend(
            _extract_simple_properties(content.core_properties, "core")
        )

        extended_files = content.docx_reader.files_of_type("extended-properties")
        findings.extend(_extract_extended_properties(extended_files))

        custom_files = content.docx_reader.files_of_type("custom-properties")
        findings.extend(_extract_custom_properties(custom_files))
        findings.extend(_extract_custom_xml_files(content.docx_reader))
    except Exception as exc:  # pragma: no cover - defensive
        findings.append(_error_finding(f"Metadata extraction failed: {exc}"))
    finally:
        content.close()

    return findings


def run_metadata(inputs: Iterable[InputSource]) -> dict:
    """Extract metadata for one or more input sources."""

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

        findings = collect_metadata(target_path)

        file_entry = {
            "path": source.display_name,
            "sha256": sha256,
            "items": [f.as_dict() for f in findings],
        }

        if temp_path:
            os.unlink(temp_path)

        merged_files.append(file_entry)

    return build_envelope(
        tool="lawdocx-metadata", files=merged_files, generated_at=generated_at
    )
