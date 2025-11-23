"""Shared data models used across lawdocx tools."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Finding:
    """Simple representation of a finding object for tool outputs."""

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

