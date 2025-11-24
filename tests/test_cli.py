"""Tests for the CLI module."""

from click.testing import CliRunner

from lawdocx.cli import main


def test_main_help():
    """Test the main command help lists available tools."""

    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Little tools for dealing with docx files" in result.output
    for command in [
        "audit",
        "metadata",
        "boilerplate",
        "todos",
        "footnotes",
        "changes",
        "comments",
        "highlights",
    ]:
        assert command in result.output


def test_version():
    """Test the version command."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
