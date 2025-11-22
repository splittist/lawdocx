# lawdocx

Little tools for dealing with docx files, useful for lawyers and their LLMs.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Create virtual environment
uv venv

# Install dependencies
uv pip install -e .

# Install development dependencies
uv pip install -e . pytest pytest-cov ruff
```

## Usage

The `lawdocx` command provides a main command with subcommands:

```bash
# Show help
lawdocx --help

# Show version
lawdocx --version

# Extract text from a DOCX file
lawdocx extract input.docx -o output.txt

# Convert DOCX file
lawdocx convert input.docx -o output.format

# Display information about a DOCX file
lawdocx info input.docx
```

## Development

### Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests with coverage
pytest -v
```

### Linting

```bash
# Run ruff linter
ruff check src/ tests/
```

## Dependencies

- **click**: Command-line interface framework
- **docx2python**: Library for extracting data from DOCX files
- **lxml**: XML processing library

### Development Dependencies

- **uv**: Package installer and resolver
- **ruff**: Fast Python linter
- **pytest**: Testing framework
- **pytest-cov**: Coverage plugin for pytest
