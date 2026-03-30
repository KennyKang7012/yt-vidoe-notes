#!/usr/bin/env python3
"""Dashboard server with note management API.

Run from repo root:
  python skills/yt-deep-note-pipeline/scripts/dashboard_server.py --port 8010
"""

from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[3]
INDEX_PATH = ROOT / "data" / "notes-index.json"


def _load_notes() -> list[dict]:
    if not INDEX_PATH.exists():
        return []
    raw = INDEX_PATH.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return []
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    return [parsed]


def _write_notes(notes: list[dict]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_markdown_path(markdown_path: str) -> Path | None:
    candidate = (ROOT / markdown_path).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None
    return candidate


class DashboardHandler(SimpleHTTPRequestHandler):
    def _send_json(self, payload: dict | list, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _api_path(self) -> str:
        return unquote(self.path.split("?", 1)[0])

    def do_GET(self) -> None:  # noqa: N802
        path = self._api_path()
        if path == "/api/notes":
            self._send_json(_load_notes())
            return
        return super().do_GET()

    def do_DELETE(self) -> None:  # noqa: N802
        path = self._api_path()
        prefix = "/api/notes/"
        if not path.startswith(prefix):
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        note_id = path[len(prefix) :].strip()
        if not note_id:
            self._send_json({"error": "Missing note id"}, status=HTTPStatus.BAD_REQUEST)
            return

        notes = _load_notes()
        target = next((n for n in notes if str(n.get("id")) == note_id), None)
        if target is None:
            self._send_json({"error": f"Note not found: {note_id}"}, status=HTTPStatus.NOT_FOUND)
            return

        notes = [n for n in notes if str(n.get("id")) != note_id]
        _write_notes(notes)

        removed_file = None
        markdown_path = str(target.get("markdown_path") or "")
        if markdown_path:
            abs_md = _safe_markdown_path(markdown_path)
            if abs_md is None:
                self._send_json(
                    {"error": "Unsafe markdown_path in index; index updated but file not removed"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            if abs_md.exists():
                abs_md.unlink()
                removed_file = str(abs_md)

        self._send_json(
            {
                "ok": True,
                "deleted_id": note_id,
                "remaining": len(notes),
                "removed_markdown_file": removed_file,
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve dashboard + notes API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()

    os.chdir(ROOT)
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Serving {ROOT} on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
