---
name: yt-deep-note-pipeline
description: Convert a YouTube URL or local MP4 into Traditional Chinese outputs, including a timestamped transcript, translated key points, and a deep-reading markdown note. Use when building or operating a YouTube learning-note workflow with storage indexing and a web dashboard for reading notes.
---

# YT Deep Note Pipeline

Create end-to-end YouTube study notes in Traditional Chinese.
Generate consistent markdown output that can be indexed by a notes database and read in a web dashboard.

## Workflow

1. Collect input.
Input is either:
- A YouTube URL (`youtube.com/watch`, `youtu.be`, or Shorts URL).
- A local MP4 path.

2. Normalize metadata.
Gather `title`, `author`, `publish_date`, `source_url_or_file`, and `language_detected`.
If metadata is missing, keep placeholders and continue.

3. Prepare transcript.
Produce sentence-level transcript with timestamps.
If transcript is not Traditional Chinese, translate to Traditional Chinese while preserving meaning and timeline.

4. Generate deep-reading note.
Load [references/yt-note-prompt-zh-tw.md](references/yt-note-prompt-zh-tw.md).
Follow its output schema strictly.
Always keep the final note in Traditional Chinese.

5. Save markdown and index entry.
Use this default note path style:
`notes/YYYY/YYYY-MM-DD-slug.md`
Update `data/notes-index.json` with one object per note:
- `id`
- `title`
- `date`
- `tags`
- `summary`
- `markdown_path`
- `source_type` (`youtube` or `mp4`)
- `source_value`
- `duration_seconds`
- `created_at`

6. Provide dashboard-ready output.
Use [references/dashboard-spec.md](references/dashboard-spec.md) as UI and data contract.
If asked for a quick prototype, reuse assets under `assets/dashboard-template/`.

## Prompting Rules

- Keep prompts deterministic and schema-first.
- Keep timeline terms accurate; do not invent timestamps.
- If transcript quality is low, include a `資料品質警告` section in the markdown.
- Prefer concise but insight-rich writing: insight over fluff.

## Output Contract

The final markdown must contain:
- `#` Title
- Video metadata block
- `## 逐字稿（含時間戳）`
- `## 深度閱讀筆記`
- `## 關鍵概念與可執行行動`
- `## 引用片段`
- `## 反思問題`
- `## 延伸資源`

## Scripts

- [scripts/render_prompt.py](scripts/render_prompt.py)
Render the prompt template with video metadata and transcript placeholders.

## References

- [references/yt-note-prompt-zh-tw.md](references/yt-note-prompt-zh-tw.md)
Main prompt template for Traditional Chinese deep-reading note generation.
- [references/dashboard-spec.md](references/dashboard-spec.md)
Dashboard information architecture and data schema.

## Assets

- [assets/dashboard-template/index.html](assets/dashboard-template/index.html)
- [assets/dashboard-template/styles.css](assets/dashboard-template/styles.css)
- [assets/dashboard-template/app.js](assets/dashboard-template/app.js)

Use these assets to quickly bootstrap a reading dashboard without redesigning from scratch.
