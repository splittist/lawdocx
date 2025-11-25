# lawdocx

> Little tools for dealing with docx files, useful for lawyers and their LLMs.

Command-line micro-tools for surfacing the mechanical artifacts that linger inside `.docx` contracts. Each subcommand reads one or more files (or `-` for stdin) and emits a newline-terminated JSON envelope that is easy for humans, scripts, or LLM prompts to consume.

## Quickstart

```bash
pip install lawdocx
lawdocx comments draft.docx --verbose
```

Every command accepts:

- One or more `PATH` arguments (globs expanded, duplicates removed; `-` reads stdin).
- `--output/-o` to write to a file instead of stdout.
- `--severity` (`info`/`warning`/`error`) to drop lower-severity findings.
- `--fail-on-findings/-f` to exit non-zero when any warning or error remains after filtering.
- `--verbose/-v` for progress plus a severity summary.

## JSON shape (stable across tools)

- Envelope: `{ lawdocx_version, tool, generated_at, files: [...] }`.
- File entries: `{ path, sha256, items: [...] }` where `path` is the CLI display name (or `stdin`).
- Findings: `{ id, type, severity, location, context, details }` with tool-specific `details`.
- Context windows come from the triggering text span; `location` always includes `story` plus paragraph indices, with extra fields per tool.

## Tools (what they actually scan)

- **`lawdocx comments`** – DOCX comment threads with resolved/done markers and optional parent pointers.
- **`lawdocx changes`** – Tracked insertions/deletions/moves across body, headers, footers, footnotes, and endnotes. Captures author/date attributes when present.
- **`lawdocx brackets`** – Finds balanced square brackets by default. Pass `-p/--pattern` multiple times to supply custom regex (DOTALL + MULTILINE). Scans body, headers, footers, footnotes, and endnotes.
- **`lawdocx todos`** – TODO/NTD/TBD/placeholder markers using a fixed regex list (e.g., `TODO`, `FIXME`, `[?]`, "client to confirm") across body, headers, and footers.
- **`lawdocx boilerplate`** – Header/footer boilerplate (draft legends, firm footers, page-number artifacts, placeholder dates, temp paths) using the built-in regex catalog. Records section number and header/footer type when available.
- **`lawdocx metadata`** – Core, extended, and custom properties plus custom XML part references. Marks extraction failures as errors.
- **`lawdocx footnotes`** – Footnote/endnote references wherever they appear (body, headers, footers, note stories). Includes rendered note text when present; flags missing text in `details.status`.
- **`lawdocx highlights`** – Highlighted runs and their colors across body, headers, footers, footnotes, and endnotes.
- **`lawdocx outline`** – Flags manual numbering (error) or suspicious numbering (warning) in body paragraphs that are not styled as headings. Uses simple pattern checks rather than rebuilding the full outline.
- **`lawdocx audit`** – Runs a selected subset of the above (`--only`/`--exclude`). Produces an outer envelope with `tools: [...]` containing each subcommand’s filtered output and totals across all tools.

## How humans might use it

- **Pre-send scrub:** Run `lawdocx boilerplate` and `lawdocx comments` before emailing a draft; combine with `--fail-on-findings` in a CI job to block warnings/errors.
- **Redline triage:** Nightly `lawdocx changes deal/*.docx > changes.json` to list insertions/deletions with context and authors for partner review.
- **Placeholder sweep:** `lawdocx brackets` and `lawdocx todos` over a folder to collect unresolved variables and TODOs into a single JSON line per file.
- **Numbering sanity check:** `lawdocx outline` on inbound paper to spot manual numbering in non-heading paragraphs that may break cross-references.

## How LLM workflows can consume it

- Use `severity` to gate reasoning (e.g., summarize only `warning`/`error`).
- Ground prompts with `context.target` for verbatim snippets and `context.before/after` for surrounding text; `location.story` + paragraph indices help build human-readable pointers.
- When reading audit output, iterate `envelope["tools"]`—each nested tool already filtered by the CLI `--severity` value.

## Contributing

- Follow the existing pattern: a small `collect_*` helper plus a `run_*` wrapper that hashes inputs, supports stdin, and returns a `build_envelope(...)` result.
- Keep severities consistent with the tool’s intent (current tools mostly emit `info` for informational data and `warning` when action may be needed).
- Add new commands to `TOOL_RUNNERS` in `src/lawdocx/cli.py` so audit mode can orchestrate them, and prefer deterministic outputs for easy downstream use.
