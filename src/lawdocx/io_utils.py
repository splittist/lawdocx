"""Shared utilities for handling CLI input and output streams."""
from __future__ import annotations

import glob
import io
import os
import sys
from dataclasses import dataclass
from typing import IO, Iterable, List, Optional, Sequence, Tuple, Union

import click


@dataclass
class InputSource:
    """Represents an input source for CLI commands."""

    path: str
    handle: IO
    is_stdin: bool = False

    @property
    def display_name(self) -> str:
        return "stdin" if self.is_stdin else self.path


InputList = List[InputSource]


def _stdin_handle(mode: str) -> IO:
    if "b" in mode:
        return sys.stdin.buffer
    return click.get_text_stream("stdin")


def resolve_inputs(paths: Sequence[str], mode: str = "rb") -> InputList:
    """Resolve CLI input arguments into open file handles.

    Expands glob patterns, de-duplicates resolved paths, and handles stdin markers.
    """

    resolved: InputList = []
    seen: set[str] = set()

    for raw_path in paths:
        if raw_path == "-":
            if any(source.is_stdin for source in resolved):
                continue
            resolved.append(InputSource(path="-", handle=_stdin_handle(mode), is_stdin=True))
            continue

        matches = glob.glob(raw_path)
        if not matches:
            raise click.ClickException(f"No files matched pattern: {raw_path}")

        for match in matches:
            absolute = os.path.abspath(match)
            if absolute in seen:
                continue
            seen.add(absolute)
            try:
                handle = open(absolute, mode)
            except OSError as exc:  # pragma: no cover - thin wrapper
                raise click.ClickException(str(exc)) from exc
            resolved.append(InputSource(path=absolute, handle=handle))

    if not resolved:
        raise click.ClickException("No input files provided")

    resolved.sort(key=lambda source: source.path)

    return resolved


def resolve_output_handle(
    output: Optional[Union[str, IO]], mode: str = "w"
) -> Tuple[IO, bool]:
    """Return an output handle and whether it should be closed by the caller."""

    if output is None:
        return click.get_text_stream("stdout"), False

    if isinstance(output, io.IOBase):
        return output, False

    if isinstance(output, str):
        if output == "-":
            return click.get_text_stream("stdout"), False
        try:
            return open(output, mode), True
        except OSError as exc:  # pragma: no cover - thin wrapper
            raise click.ClickException(str(exc)) from exc

    raise click.ClickException("Invalid output destination")


def close_inputs(inputs: Iterable[InputSource]) -> None:
    """Close any non-stdin input handles."""

    for source in inputs:
        if not source.is_stdin:
            source.handle.close()
