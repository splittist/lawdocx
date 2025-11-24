"""Shared utilities for hashing, timestamps, and JSON envelope creation."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import IO, Iterable

from lawdocx import __version__


def utc_timestamp() -> str:
    """Return an ISO 8601 UTC timestamp suitable for envelopes and logs."""

    return datetime.now(timezone.utc).isoformat()


def hash_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest for a bytes payload."""

    return hashlib.sha256(data).hexdigest()


def hash_file(path: str, *, chunk_size: int = 8192) -> str:
    """Return the SHA-256 hex digest for a file without loading it entirely into memory."""

    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            sha.update(chunk)
    return sha.hexdigest()


def build_envelope(*, tool: str, files: Iterable[dict], generated_at: str | None = None) -> dict:
    """Construct a standard lawdocx JSON envelope for tool outputs."""

    return {
        "lawdocx_version": __version__,
        "tool": tool,
        "generated_at": generated_at or utc_timestamp(),
        "files": list(files),
    }


def dump_json_line(data: dict, output_handle: IO) -> None:
    """Serialize a dictionary as JSON followed by a newline to support streaming outputs."""

    json.dump(data, output_handle)
    output_handle.write("\n")


SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}


def filter_files_by_severity(files: Iterable[dict], minimum: str) -> list[dict]:
    """Return file entries containing only findings at or above ``minimum`` severity."""

    threshold = SEVERITY_ORDER[minimum]
    filtered: list[dict] = []

    for entry in files:
        items = [
            item
            for item in entry.get("items", [])
            if SEVERITY_ORDER.get(item.get("severity", "info"), 0) >= threshold
        ]
        filtered.append({**entry, "items": items})

    return filtered


def summarize_severities(files: Iterable[dict]) -> dict[str, int]:
    """Count findings by severity across file entries."""

    totals = {"info": 0, "warning": 0, "error": 0}

    for entry in files:
        for item in entry.get("items", []):
            severity = item.get("severity", "info")
            if severity in totals:
                totals[severity] += 1

    return totals


def text_context(
    text: str, start: int, end: int, *, window: int = 100, target_limit: int = 500
) -> dict:
    """Return a context dictionary describing text around a target span.

    Parameters
    ----------
    text:
        The full text body.
    start, end:
        The character offsets for the target span within ``text``.
    window:
        Number of characters to include before and after the target span.
    target_limit:
        Maximum number of characters to include from the target span itself.
    """

    return {
        "before": text[max(0, start - window) : start],
        "target": text[start:end][:target_limit],
        "after": text[end : end + window],
    }
