"""Command-line interface for lawdocx."""

import click

from lawdocx import __version__, io_utils
from lawdocx.boilerplate import run_boilerplate
from lawdocx.brackets import run_brackets
from lawdocx.changes import run_changes
from lawdocx.comments import run_comments
from lawdocx.footnotes import run_footnotes
from lawdocx.highlights import run_highlights
from lawdocx.metadata import run_metadata
from lawdocx.outline import run_outline
from lawdocx.todos import run_todos
from lawdocx.utils import dump_json_line, filter_files_by_severity, summarize_severities


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx):
    """Little tools for dealing with docx files, useful for lawyers and their LLMs."""
    ctx.ensure_object(dict)


def _common_options(func):
    func = click.argument("paths", nargs=-1, required=True)(func)
    func = click.option(
        "--output",
        "-o",
        type=click.Path(),
        default=None,
        show_default="stdout",
        help="Output file path or '-' for stdout.",
    )(func)
    func = click.option(
        "--verbose",
        "-v",
        is_flag=True,
        help="Show progress and a summary of findings.",
    )(func)
    func = click.option(
        "--fail-on-findings",
        "-f",
        is_flag=True,
        help="Exit with status 1 if warning or error findings are present.",
    )(func)
    func = click.option(
        "--severity",
        type=click.Choice(["info", "warning", "error"], case_sensitive=False),
        default="info",
        show_default=True,
        help="Minimum severity to include in the output.",
    )(func)
    return func


def _execute_tool(
    runner,
    paths,
    output,
    verbose: bool,
    fail_on_findings: bool,
    severity: str,
    **kwargs,
):
    inputs = io_utils.resolve_inputs(paths, mode="rb")
    output_handle, should_close = io_utils.resolve_output_handle(output, mode="w")

    try:
        if verbose:
            click.echo(f"Processing {len(inputs)} file(s)...", err=True)
            for source in inputs:
                click.echo(f"  - {source.display_name}", err=True)

        envelope = runner(inputs, **kwargs)
        filtered_files = filter_files_by_severity(envelope.get("files", []), severity.lower())
        summary = summarize_severities(filtered_files)

        dump_json_line({**envelope, "files": filtered_files}, output_handle)

        if verbose:
            click.echo(
                "Summary: "
                f"info={summary['info']} warning={summary['warning']} error={summary['error']}",
                err=True,
            )

        if fail_on_findings and (summary["warning"] or summary["error"]):
            raise SystemExit(1)
    finally:
        if should_close:
            output_handle.close()
        io_utils.close_inputs(inputs)


@main.command()
@_common_options
def metadata(paths, output, verbose, fail_on_findings, severity):
    """Extract metadata from one or more DOCX files."""

    _execute_tool(
        run_metadata,
        paths,
        output,
        verbose,
        fail_on_findings,
        severity,
    )


@main.command()
@_common_options
def comments(paths, output, verbose, fail_on_findings, severity):
    """Extract threaded comments with resolved status."""

    _execute_tool(
        run_comments,
        paths,
        output,
        verbose,
        fail_on_findings,
        severity,
    )


@main.command()
@_common_options
@click.option(
    "--pattern",
    "-p",
    multiple=True,
    help="Regex pattern to match (may be repeated). Defaults to balanced square brackets.",
)
def brackets(paths, output, verbose, fail_on_findings, severity, pattern):
    """Detect bracketed text (or custom regex matches) in DOCX files."""

    _execute_tool(
        run_brackets,
        paths,
        output,
        verbose,
        fail_on_findings,
        severity,
        patterns=pattern or None,
    )


@main.command()
@_common_options
def boilerplate(paths, output, verbose, fail_on_findings, severity):
    """Detect boilerplate legends and page artifacts in DOCX files."""

    _execute_tool(
        run_boilerplate,
        paths,
        output,
        verbose,
        fail_on_findings,
        severity,
    )


@main.command()
@_common_options
def todos(paths, output, verbose, fail_on_findings, severity):
    """Detect TODO/NTD/placeholder markers in DOCX files."""

    _execute_tool(
        run_todos,
        paths,
        output,
        verbose,
        fail_on_findings,
        severity,
    )


@main.command()
@_common_options
def footnotes(paths, output, verbose, fail_on_findings, severity):
    """Extract footnotes and endnotes with contextual locations."""

    _execute_tool(
        run_footnotes,
        paths,
        output,
        verbose,
        fail_on_findings,
        severity,
    )


@main.command()
@_common_options
def changes(paths, output, verbose, fail_on_findings, severity):
    """Extract tracked changes (insertions, deletions, moves) from DOCX files."""

    _execute_tool(
        run_changes,
        paths,
        output,
        verbose,
        fail_on_findings,
        severity,
    )


@main.command()
@_common_options
def highlights(paths, output, verbose, fail_on_findings, severity):
    """Extract background highlighting from DOCX files."""

    _execute_tool(
        run_highlights,
        paths,
        output,
        verbose,
        fail_on_findings,
        severity,
    )


@main.command()
@_common_options
def outline(paths, output, verbose, fail_on_findings, severity):
    """Detect outline numbering issues in DOCX files."""

    _execute_tool(
        run_outline,
        paths,
        output,
        verbose,
        fail_on_findings,
        severity,
    )


if __name__ == "__main__":
    main()
