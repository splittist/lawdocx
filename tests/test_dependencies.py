"""Tests to verify required dependencies are available."""


def test_click_import():
    """Test that click can be imported."""
    import click
    assert click is not None


def test_docx2python_import():
    """Test that docx2python can be imported."""
    import docx2python
    assert docx2python is not None


def test_lxml_import():
    """Test that lxml can be imported."""
    import lxml
    assert lxml is not None
