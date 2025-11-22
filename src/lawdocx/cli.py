"""Command-line interface for lawdocx."""

import click

from lawdocx import __version__


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


if __name__ == "__main__":
    main()
