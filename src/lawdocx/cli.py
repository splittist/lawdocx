"""Command-line interface for lawdocx."""

import click

from lawdocx import __version__, io_utils
from lawdocx.boilerplate import run_boilerplate
from lawdocx.brackets import run_brackets
from lawdocx.comments import run_comments
from lawdocx.changes import run_changes
from lawdocx.highlights import run_highlights
from lawdocx.footnotes import run_footnotes
from lawdocx.metadata import run_metadata
from lawdocx.todos import run_todos


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx):
    """Little tools for dealing with docx files, useful for lawyers and their LLMs."""
    ctx.ensure_object(dict)


@main.command()
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    show_default="stdout",
    help="Output file path or '-' for stdout.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Combine metadata from multiple files into a single envelope.",
)
def metadata(paths, output, merge):
    """Extract metadata from one or more DOCX files."""

    inputs = io_utils.resolve_inputs(paths, mode="rb")
    output_handle, should_close = io_utils.resolve_output_handle(output, mode="w")

    try:
        run_metadata(inputs, merge, output_handle)
    finally:
        if should_close:
            output_handle.close()
        io_utils.close_inputs(inputs)


@main.command()
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    show_default="stdout",
    help="Output file path or '-' for stdout.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Combine comment findings from multiple files into a single envelope.",
)
def comments(paths, output, merge):
    """Extract threaded comments with resolved status."""

    inputs = io_utils.resolve_inputs(paths, mode="rb")
    output_handle, should_close = io_utils.resolve_output_handle(output, mode="w")

    try:
        run_comments(inputs, merge, output_handle)
    finally:
        if should_close:
            output_handle.close()
        io_utils.close_inputs(inputs)


@main.command()
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    show_default="stdout",
    help="Output file path or '-' for stdout.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Combine bracket findings from multiple files into a single envelope.",
)
@click.option(
    "--pattern",
    "-p",
    multiple=True,
    help="Regex pattern to match (may be repeated). Defaults to balanced square brackets.",
)
def brackets(paths, output, merge, pattern):
    """Detect bracketed text (or custom regex matches) in DOCX files."""

    inputs = io_utils.resolve_inputs(paths, mode="rb")
    output_handle, should_close = io_utils.resolve_output_handle(output, mode="w")

    try:
        run_brackets(inputs, merge, output_handle, patterns=pattern or None)
    finally:
        if should_close:
            output_handle.close()
        io_utils.close_inputs(inputs)


@main.command()
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    show_default="stdout",
    help="Output file path or '-' for stdout.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Combine boilerplate findings from multiple files into a single envelope.",
)
def boilerplate(paths, output, merge):
    """Detect boilerplate legends and page artifacts in DOCX files."""

    inputs = io_utils.resolve_inputs(paths, mode="rb")
    output_handle, should_close = io_utils.resolve_output_handle(output, mode="w")

    try:
        run_boilerplate(inputs, merge, output_handle)
    finally:
        if should_close:
            output_handle.close()
        io_utils.close_inputs(inputs)


@main.command()
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    show_default="stdout",
    help="Output file path or '-' for stdout.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Combine TODO findings from multiple files into a single envelope.",
)
def todos(paths, output, merge):
    """Detect TODO/NTD/placeholder markers in DOCX files."""

    inputs = io_utils.resolve_inputs(paths, mode="rb")
    output_handle, should_close = io_utils.resolve_output_handle(output, mode="w")

    try:
        run_todos(inputs, merge, output_handle)
    finally:
        if should_close:
            output_handle.close()
        io_utils.close_inputs(inputs)


@main.command()
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    show_default="stdout",
    help="Output file path or '-' for stdout.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Combine footnote findings from multiple files into a single envelope.",
)
def footnotes(paths, output, merge):
    """Extract footnotes and endnotes with contextual locations."""

    inputs = io_utils.resolve_inputs(paths, mode="rb")
    output_handle, should_close = io_utils.resolve_output_handle(output, mode="w")

    try:
        run_footnotes(inputs, merge, output_handle)
    finally:
        if should_close:
            output_handle.close()
        io_utils.close_inputs(inputs)


@main.command()
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    show_default="stdout",
    help="Output file path or '-' for stdout.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Combine tracked changes from multiple files into a single envelope.",
)
def changes(paths, output, merge):
    """Extract tracked changes (insertions, deletions, moves) from DOCX files."""

    inputs = io_utils.resolve_inputs(paths, mode="rb")
    output_handle, should_close = io_utils.resolve_output_handle(output, mode="w")

    try:
        run_changes(inputs, merge, output_handle)
    finally:
        if should_close:
            output_handle.close()
        io_utils.close_inputs(inputs)


@main.command()
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    show_default="stdout",
    help="Output file path or '-' for stdout.",
)
@click.option(
    "--merge",
    is_flag=True,
    help="Combine highlight findings from multiple files into a single envelope.",
)
def highlights(paths, output, merge):
    """Extract background highlighting from DOCX files."""

    inputs = io_utils.resolve_inputs(paths, mode="rb")
    output_handle, should_close = io_utils.resolve_output_handle(output, mode="w")

    try:
        run_highlights(inputs, merge, output_handle)
    finally:
        if should_close:
            output_handle.close()
        io_utils.close_inputs(inputs)


if __name__ == "__main__":
    main()
