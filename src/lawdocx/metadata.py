"""Metadata handling utilities for lawdocx."""
from __future__ import annotations

from typing import Iterable

from lawdocx.io_utils import InputSource


def run_metadata(inputs: Iterable[InputSource], merge: bool, output_handle) -> None:
    """Placeholder metadata runner that reports received inputs.

    Actual metadata extraction will be implemented in future iterations.
    """

    if merge:
        output_handle.write("Merging metadata across inputs is not yet implemented.\n")

    for source in inputs:
        output_handle.write(f"Metadata extraction is not yet implemented for {source.display_name}.\n")
