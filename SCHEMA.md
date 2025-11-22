# lawdocx JSON Schema (v1)

Every tool emits **exactly** this structure.  
No fields are ever added or removed without a major version bump.

## Top-level envelope

```json
{
  "lawdocx_version": "1.2.3",                    // version of the lawdocx package
  "tool": "lawdocx-comments",                    // exact sub-command name
  "generated_at": "2025-11-22T14:27:12Z",        // ISO-8601 UTC
  "files": [                                     // always present (even for single file)
    {
      "path": "contracts/msa-v9.docx",
      "sha256": "a1b2c3…",                       // optional but encouraged
      "items": [ … ]                             // zero or more findings (see below)
    }
  ]
}
```

When `--merge` is used, `files` contains every processed document.  
Without `--merge`, each tool writes one JSON file per input file (still with a single-item `files` array).

## The Finding object (inside `items`)

```json
{
  "id": "f9e8d7c6",                              // stable random UUID fragment
  "type": "comment | insertion | deletion | bracket | boilerplate | …",
  "severity": "error | warning | info",         // fixed vocabulary
  "location": {
    "file_index": 0,                             // index into top-level files array
    "story": "main | header--Section1--first | footer--Section2--odd | footnote--7 | endnote--3 | comment | metadata",
    "paragraph_index_start": 84,                 // inclusive, 0-based within the story
    "paragraph_index_end": 84,                   // inclusive; same as start for single-para hits
    "comment_id": "3"                            // only present for comment-type findings
  },
  "context": {
    "before": "…last 100 chars before the hit…",
    "target": "the exact flagged text (or up to 500 chars)",
    "after":  "first 100 chars after the hit…"
  },
  "details": {                                   // type-specific free-form object
    "author": "john.doe@lawfirm.com",            // comments, changes
    "date": "2025-11-15T10:22:00Z",               // ISO-8601 when available
    "resolved": false,                           // boolean for comments
    "inserted_text": "material",                 // changes
    "deleted_text": "without cause",             // changes
    "matched_pattern": "DRAFT",                  // boilerplate / todos
    "highlight_color": "yellow",                 // named highlight color
    "reference_number": "7",                     // footnotes
    "style_name": "Heading 1",                   // outline / terms
    "raw_text": "[insert cap here]",             // brackets / todos
    "property_category": "core",                // metadata: core | extended | custom | revision
    "property_name": "last_author",             // metadata: raw property name
    "property_value": "Jane Smith",             // metadata: raw property value (stringified)
    "property_datatype": "string",              // metadata: raw datatype from the document
    "property_revision_id": "5"                  // metadata: revision identifier when captured
  },
}
```

For metadata-only findings, `location.story` is `metadata` and both paragraph indexes are set to `0`. The metadata tool reports the raw property category, name, value, datatype, and (when present) the revision identifier without inference or reformatting.

### Fixed severity meanings

| severity | meaning for a human reviewer                |
|----------|---------------------------------------------|
| error    | Almost certainly must be fixed before sending |
| warning  | Very likely needs attention                |
| info     | FYI / context only                          |

### Fixed type vocabulary (closed set – new types require major version)

| type               | tool that emits it           |
|--------------------|------------------------------|
| comment            | comments                     |
| insertion / deletion / move_from / move_to / format_change | changes |
| bracket            | brackets                     |
| todo_marker        | todos                        |
| boilerplate        | boilerplate                  |
| footnote / endnote | footnotes                    |
| highlight          | highlights                   |
| manual_numbering   | outline                      |
| heading_gap        | outline                      |
| term_inconsistency | terms                        |
| metadata           | metadata                     |

## Guarantees

1. Every finding contains a valid `location` that can be traced back to the original .docx.
2. `context.target` is always the exact text that triggered the finding (never summarised or re-worded).
3. No finding is ever emitted twice for the same trigger in the same file.
4. Tools never throw exceptions on real-world BigLaw files (they degrade gracefully and record the error in the JSON if something truly bizarre happens).

Consumers (LLMs, scripts, LangChain tools) can therefore trust the output 100 % for location and content.
