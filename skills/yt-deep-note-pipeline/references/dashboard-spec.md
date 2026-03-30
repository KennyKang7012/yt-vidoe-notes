# Dashboard Spec

## Purpose

Provide a web reading dashboard for generated YouTube deep-reading notes.

## Information Architecture

- Left sidebar:
- Search box
- Tag filters
- Notes count

- Main content:
- Note list cards with title, summary, tags, date
- Detail panel rendering markdown content

## Data Contract

Use `data/notes-index.json` as list source.

Each item schema:

```json
{
  "id": "string",
  "title": "string",
  "date": "YYYY-MM-DD",
  "tags": ["string"],
  "summary": "string",
  "markdown_path": "notes/YYYY/file.md",
  "source_type": "youtube|mp4",
  "source_value": "string",
  "duration_seconds": 0,
  "created_at": "ISO8601"
}
```

## UX Rules

- Default sort: `date` descending.
- Search against title, summary, and tags.
- When clicking a card, load markdown and render in the right panel.
- If markdown load fails, show a retryable inline error.
