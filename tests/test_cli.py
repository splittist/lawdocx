"""Tests for the CLI module."""

from click.testing import CliRunner

from lawdocx.cli import main


def test_main_help():
    """Test the main command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Little tools for dealing with docx files" in result.output


def test_version():
    """Test the version command."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_extract_help():
    """Test the extract command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["extract", "--help"])
    assert result.exit_code == 0
    assert "Extract text from a DOCX file" in result.output


def test_convert_help():
    """Test the convert command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["convert", "--help"])
    assert result.exit_code == 0
    assert "Convert DOCX file to another format" in result.output


def test_info_help():
    """Test the info command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["info", "--help"])
    assert result.exit_code == 0
    assert "Display information about a DOCX file" in result.output
