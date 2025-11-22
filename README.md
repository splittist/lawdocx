# lawdocx

Little tools for dealing with .docx files – useful for lawyers and their LLMs.

```bash
pip install lawdocx
lawdocx audit deals/**/*.docx --merge > audit-2025-Q4.json
```

## What it is

A small, deliberately simple collection of command-line tools that extract the things people routinely leave behind in Word contracts:

- unresolved comments (including modern threaded/replied/done comments)  
- tracked changes (insertions, deletions, moves, formatting)  
- square-bracket placeholders and TODO/NTD markers  
- DRAFT watermarks, law-firm footers, page-numbering boilerplate  
- document metadata and custom properties  
- footnotes and endnotes (full text)  
- text highlighting  
- heading hierarchy and manual numbering problems  
- inconsistent defined-terms  

Each tool reads one or more .docx files and writes clean, predictable JSON. That JSON is designed to be consumed directly by LLMs, scripts, or pandas.

## Why this exists

Commercial contract-review platforms are excellent at deep analysis but are expensive and sometimes over-confident. The simple mechanical questions (“are there still comments/brackets/boilerplate?”) are often answered badly or not at all.

These tools answer only those mechanical questions.

## Tools

| command                     | purpose                                              | covers headers/footers/footnotes/comments |
|-----------------------------|------------------------------------------------------|--------------------------------------------|
| `lawdocx comments`          | modern threaded comments + resolved status           | Yes                                        |
| `lawdocx changes`           | tracked changes + authors                            | Yes                                        |
| `lawdocx brackets`          | [anything in square brackets]                        | Yes                                        |
| `lawdocx todos`             | TODO / NTD / [?] etc.                                | Yes                                        |
| `lawdocx boilerplate`       | DRAFT, law-firm footers, Page X of Y, [Date]…        | Yes                                        |
| `lawdocx metadata`          | core/extended/custom properties, revision history   | –                                          |
| `lawdocx footnotes`         | full footnote and endnote text                       | Yes                                        |
| `lawdocx highlights`        | background highlighting                              | Yes                                        |
| `lawdocx outline`           | heading hierarchy + manual numbering detection       | Yes                                        |
| `lawdocx terms`             | inconsistent defined-term styling                    | Yes                                        |
| `lawdocx audit`             | runs everything and optionally merges output         | Yes                                        |

Every tool works on a single file, multiple files, globs, or stdin.

## Example

```bash
# Quick safety check before sending
lawdocx boilerplate final.docx && lawdocx comments final.docx && echo "Clean"

# Full batch audit of a folder
lawdocx audit incoming/*.docx --merge > incoming-audit.json
```

The resulting JSON uses a single stable schema (documented in SCHEMA.md) so downstream prompts or scripts never break.

## Design principles

- Each tool ≤ 150 lines  
- No configuration files in v1 (hard-coded patterns are honest and predictable)  
- Primary parser is `docx2python`; minimal lxml only where absolutely required  
- Batch mode from day one  
- All findings include precise location information  
- Intelligence belongs in the consumer (LLM, script, human), not the extractor

## Installation

```bash
pip install lawdocx
```

or from source:

```bash
pip install git+https://github.com/yourname/lawdocx.git
```

## Contributing

Contributions are very welcome. Please keep new tools small, focused, and faithful to the pattern established by the existing ones. Tests should include real (anonymised) .docx samples.

## License

Apache License 2.0 (see LICENSE)

Enjoy the calm of knowing exactly what is hiding in every Word file.