# lawdocx JSON Schema

This document describes the JSON output format for all lawdocx tools. The machine-readable schema is in `schema.json`.

## Top-level Envelope

Every tool emits this structure:

```json
{
  "lawdocx_version": "0.2.0",
  "tool": "lawdocx-comments",
  "generated_at": "2025-11-22T14:27:12.123456+00:00",
  "files": [
    {
      "path": "/path/to/contract.docx",
      "sha256": "a1b2c3d4e5f6...(64 hex characters)",
      "items": []
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `lawdocx_version` | string | Version of the lawdocx package |
| `tool` | string | Tool name (see [Tools](#tools)) |
| `generated_at` | string | ISO 8601 UTC timestamp |
| `files` | array | One entry per input file processed |

### File Entry

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | Absolute file path or `stdin` for piped input |
| `sha256` | string | SHA-256 hash of the input file (64 hex chars) |
| `items` | array | Findings detected in this file |

## Finding Object

Each finding in the `items` array has this structure:

```json
{
  "id": "a1b2c3d4",
  "type": "comment",
  "severity": "info",
  "location": {
    "story": "body",
    "paragraph_index_start": 5,
    "paragraph_index_end": 5
  },
  "context": {
    "before": "preceding text...",
    "target": "flagged text",
    "after": "following text..."
  },
  "details": {}
}
```

### Base Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Random 8-character hex identifier |
| `type` | string | Finding type (see [Type Vocabulary](#type-vocabulary)) |
| `severity` | string | `info`, `warning`, or `error` |
| `location` | object | Where the finding occurs in the document |
| `context` | object | Text surrounding the finding |
| `details` | object | Tool-specific additional data |

### Severity Meanings

| Severity | Meaning |
|----------|---------|
| `error` | Must be fixed before sending |
| `warning` | Likely needs attention |
| `info` | Informational only |

### Type Vocabulary

| Type | Tool | Description |
|------|------|-------------|
| `comment` | comments | Document comment |
| `insertion` | changes | Tracked insertion |
| `deletion` | changes | Tracked deletion |
| `move_from` | changes | Tracked move source |
| `move_to` | changes | Tracked move destination |
| `bracket` | brackets | Bracketed text or regex match |
| `todo` | todos | TODO/placeholder marker |
| `boilerplate` | boilerplate | Boilerplate text in header/footer |
| `footnote` | footnotes | Footnote reference |
| `endnote` | footnotes | Endnote reference |
| `highlight` | highlights | Highlighted text |
| `outline` | outline | Numbering issue |
| `metadata` | metadata | Document metadata property |

## Location Object

The base location fields are present in all findings:

| Field | Type | Description |
|-------|------|-------------|
| `story` | string | Document story (see below) |
| `paragraph_index_start` | integer/null | 0-based start paragraph index |
| `paragraph_index_end` | integer/null | 0-based end paragraph index (inclusive) |

### Story Values

| Story | Description |
|-------|-------------|
| `body` | Main document body |
| `header` | Document header |
| `footer` | Document footer |
| `footnote` | Footnotes section |
| `endnote` | Endnotes section |
| `comment` | Comment text (used when anchor not found) |
| `metadata` | Document properties |
| `main` | Main body (used by footnotes tool) |
| `footnote--{id}` | Specific footnote by ID |
| `endnote--{id}` | Specific endnote by ID |
| `header--Section{n}--{type}` | Section-specific header |
| `footer--Section{n}--{type}` | Section-specific footer |

### Tool-Specific Location Fields

**Comments tool:**
| Field | Type | Description |
|-------|------|-------------|
| `comment_id` | string | XML comment ID |
| `target_location` | object | Location within the comment text |
| `anchor_fallback` | boolean | True if anchor range not found |

**Boilerplate tool:**
| Field | Type | Description |
|-------|------|-------------|
| `section_number` | integer | 1-based document section number |
| `header_type` | string | Header/footer type: `default`, `first`, or `even` |

## Context Object

| Field | Type | Description |
|-------|------|-------------|
| `before` | string | Up to 100 characters before the target |
| `target` | string | The flagged text (up to 500 characters) |
| `after` | string | Up to 100 characters after the target |

## Details by Tool

### comments

| Field | Type | Description |
|-------|------|-------------|
| `resolved` | boolean | Whether the comment is marked resolved |
| `comment_text` | string | Full comment text (paragraphs joined with `\n`) |
| `author` | string | Comment author (if available) |
| `initials` | string | Author initials (if available) |
| `date` | string | Comment date ISO 8601 (if available) |
| `parent_comment_id` | string | Parent comment ID for threaded replies |
| `context_fallback` | string | Set to `"comment_text"` when anchor not found |

### changes

| Field | Type | Description |
|-------|------|-------------|
| `inserted_text` | string | Inserted text (for `insertion` and `move_to`) |
| `deleted_text` | string | Deleted text (for `deletion` and `move_from`) |
| `author` | string | Change author (if available) |
| `date` | string | Change date ISO 8601 (if available) |

### brackets

| Field | Type | Description |
|-------|------|-------------|
| `matched_pattern` | string | Regex pattern that matched (or `"default_brackets"`) |
| `raw_text` | string | The matched bracketed text |

### todos

| Field | Type | Description |
|-------|------|-------------|
| `matched_pattern` | string | The pattern that triggered the match |
| `raw_text` | string | The matched text |

### boilerplate

| Field | Type | Description |
|-------|------|-------------|
| `matched_pattern` | string | The boilerplate text that matched |

### footnotes

| Field | Type | Description |
|-------|------|-------------|
| `note_type` | string | `"footnote"` or `"endnote"` |
| `note_id` | integer | Note reference ID |
| `note_text` | string | Full note text content |
| `status` | string | `"missing note text"` when note content not found |

### highlights

| Field | Type | Description |
|-------|------|-------------|
| `highlight_color` | string | Highlight color name (e.g., `"yellow"`, `"green"`) |

### outline

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | `"manual_numbering"` or `"suspicious_numbering"` |
| `style_name` | string | Paragraph style name |

### metadata

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Property name |
| `category` | string | `"core"`, `"extended"`, `"custom"`, or `"custom-xml"` |
| `raw_value` | string | Property value as string |
| `datatype` | string | Data type (for custom properties) |
| `count` | integer | Count (for custom XML parts) |
| `paths` | array | Paths (for custom XML parts) |
| `status` | string | Status message (e.g., `"missing document.xml.rels"`) |

### Error Details

When a tool encounters an error, the details object contains:

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | `"error"` |
| `message` | string | Error description |

## Tools

| Tool Name | Command | Description |
|-----------|---------|-------------|
| `lawdocx-metadata` | `lawdocx metadata` | Extract document metadata |
| `lawdocx-comments` | `lawdocx comments` | Extract comments with threading |
| `lawdocx-brackets` | `lawdocx brackets` | Detect bracketed text |
| `lawdocx-boilerplate` | `lawdocx boilerplate` | Detect boilerplate in headers/footers |
| `lawdocx-todos` | `lawdocx todos` | Detect TODO markers |
| `lawdocx-footnotes` | `lawdocx footnotes` | Extract footnotes and endnotes |
| `lawdocx-changes` | `lawdocx changes` | Extract tracked changes |
| `lawdocx-highlights` | `lawdocx highlights` | Extract highlighted text |
| `lawdocx-outline` | `lawdocx outline` | Detect numbering issues |
| `lawdocx-audit` | `lawdocx audit` | Run all tools combined |

## Audit Envelope

The audit command wraps all tool outputs:

```json
{
  "lawdocx_version": "0.1.0",
  "tool": "lawdocx-audit",
  "generated_at": "2025-11-22T14:27:12.123456+00:00",
  "files": [],
  "tools": [
    { /* nested tool envelope */ },
    { /* nested tool envelope */ }
  ]
}
```

The `tools` array contains the complete output envelope from each tool run.

## Guarantees

1. Every finding contains a valid `location` traceable to the original `.docx`.
2. `context.target` contains the exact flagged text (not summarized).
3. Tools degrade gracefully on malformed files, recording errors in the JSON.
4. The `sha256` field is always present and correct.
