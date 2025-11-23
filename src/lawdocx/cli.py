"""Command-line interface for lawdocx."""

import click

from lawdocx import __version__, io_utils
from lawdocx.boilerplate import run_boilerplate
from lawdocx.metadata import run_metadata
from lawdocx.todos import run_todos


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx):
    """Little tools for dealing with docx files, useful for lawyers and their LLMs."""
    ctx.ensure_object(dict)


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output file path")
def extract(input_file, output):
    """Extract text from a DOCX file."""
    click.echo(f"Extracting text from {input_file}")
    if output:
        click.echo(f"Output will be saved to {output}")
    # Placeholder for actual implementation
    click.echo("This is a placeholder for text extraction functionality")


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output file path")
def convert(input_file, output):
    """Convert DOCX file to another format."""
    click.echo(f"Converting {input_file}")
    if output:
        click.echo(f"Output will be saved to {output}")
    # Placeholder for actual implementation
    click.echo("This is a placeholder for conversion functionality")


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
def info(input_file):
    """Display information about a DOCX file."""
    click.echo(f"Getting info for {input_file}")
    # Placeholder for actual implementation
    click.echo("This is a placeholder for info functionality")


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


if __name__ == "__main__":
    main()
