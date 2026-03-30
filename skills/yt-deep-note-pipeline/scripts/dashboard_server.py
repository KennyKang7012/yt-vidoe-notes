#!/usr/bin/env python3
"""Dashboard server with note management API.

Run from repo root:
  python skills/yt-deep-note-pipeline/scripts/dashboard_server.py --port 8010
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[3]
INDEX_PATH = ROOT / "data" / "notes-index.json"
UNDO_STATE_PATH = ROOT / "data" / "dashboard-undo-state.json"
AUTO_GIT_COMMIT = True
UNDO_MAX_ENTRIES = 10


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


def _normalize_undo_entries(entries: object) -> list[dict]:
    if not isinstance(entries, list):
        return []

    normalized: list[dict] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        commit_hash = str(item.get("delete_commit_hash") or "").strip()
        if not commit_hash:
            continue
        normalized.append(
            {
                "delete_commit_hash": commit_hash,
                "note_id": str(item.get("note_id") or "").strip(),
                "note_title": str(item.get("note_title") or "").strip(),
                "created_at": str(item.get("created_at") or "").strip(),
            }
        )
    return normalized


def _load_undo_state() -> dict:
    if not UNDO_STATE_PATH.exists():
        return {"can_undo": False, "max_entries": UNDO_MAX_ENTRIES, "entries": []}

    raw = UNDO_STATE_PATH.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return {"can_undo": False, "max_entries": UNDO_MAX_ENTRIES, "entries": []}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"can_undo": False, "max_entries": UNDO_MAX_ENTRIES, "entries": []}

    entries: list[dict]
    if isinstance(parsed, dict):
        if isinstance(parsed.get("entries"), list):
            entries = _normalize_undo_entries(parsed.get("entries"))
        else:
            # backward compatibility: old single-entry format
            single = {
                "delete_commit_hash": str(parsed.get("delete_commit_hash") or "").strip(),
                "note_id": str(parsed.get("note_id") or "").strip(),
                "note_title": str(parsed.get("note_title") or "").strip(),
                "created_at": str(parsed.get("created_at") or "").strip(),
            }
            entries = [single] if single["delete_commit_hash"] else []
    else:
        entries = []

    entries = entries[:UNDO_MAX_ENTRIES]
    return {
        "can_undo": len(entries) > 0,
        "max_entries": UNDO_MAX_ENTRIES,
        "entries": entries,
    }


def _write_undo_state(entries: list[dict]) -> None:
    entries = _normalize_undo_entries(entries)[:UNDO_MAX_ENTRIES]
    UNDO_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "max_entries": UNDO_MAX_ENTRIES,
        "entries": entries,
    }
    UNDO_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_undo_entry(commit_hash: str, note_id: str, note_title: str) -> None:
    state = _load_undo_state()
    entries = state.get("entries", []) if isinstance(state, dict) else []
    entries = _normalize_undo_entries(entries)

    # de-duplicate by commit hash
    entries = [e for e in entries if e.get("delete_commit_hash") != commit_hash]
    entries.insert(
        0,
        {
            "delete_commit_hash": commit_hash,
            "note_id": note_id,
            "note_title": note_title,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _write_undo_state(entries)


def _remove_undo_entry(commit_hash: str) -> None:
    state = _load_undo_state()
    entries = state.get("entries", []) if isinstance(state, dict) else []
    entries = [e for e in _normalize_undo_entries(entries) if e.get("delete_commit_hash") != commit_hash]
    _write_undo_state(entries)


def _safe_markdown_path(markdown_path: str) -> Path | None:
    candidate = (ROOT / markdown_path).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None
    return candidate


def _git_run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _git_autocommit_delete(note_id: str, note_title: str, removed_file: Path | None) -> dict:
    if not AUTO_GIT_COMMIT:
        return {"enabled": False, "committed": False, "reason": "disabled"}

    inside = _git_run(["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0:
        return {
            "enabled": True,
            "committed": False,
            "reason": "not_a_git_repo",
            "error": inside.stderr.strip() or inside.stdout.strip(),
        }

    add_paths = [str(INDEX_PATH.relative_to(ROOT)).replace("\\", "/")]
    if removed_file is not None:
        add_paths.append(str(removed_file.relative_to(ROOT)).replace("\\", "/"))

    add_proc = _git_run(["add", "--", *add_paths])
    if add_proc.returncode != 0:
        return {
            "enabled": True,
            "committed": False,
            "reason": "git_add_failed",
            "error": add_proc.stderr.strip() or add_proc.stdout.strip(),
        }

    staged = _git_run(["diff", "--cached", "--quiet"])
    if staged.returncode == 0:
        return {"enabled": True, "committed": False, "reason": "no_changes"}

    message = f"chore(notes): delete {note_id}"
    commit_proc = _git_run(["commit", "-m", message])
    if commit_proc.returncode != 0:
        return {
            "enabled": True,
            "committed": False,
            "reason": "git_commit_failed",
            "error": commit_proc.stderr.strip() or commit_proc.stdout.strip(),
        }

    rev = _git_run(["rev-parse", "--short", "HEAD"])
    commit_hash = rev.stdout.strip() if rev.returncode == 0 else ""

    result = {
        "enabled": True,
        "committed": True,
        "hash": commit_hash,
        "message": message,
        "note_id": note_id,
        "note_title": note_title,
    }

    if commit_hash:
        _append_undo_entry(commit_hash=commit_hash, note_id=note_id, note_title=note_title)

    return result


def _git_revert_delete(commit_hash: str | None = None) -> dict:
    inside = _git_run(["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0:
        return {
            "ok": False,
            "reason": "not_a_git_repo",
            "error": inside.stderr.strip() or inside.stdout.strip(),
        }

    target = (commit_hash or "").strip()
    if not target:
        state = _load_undo_state()
        entries = state.get("entries", []) if isinstance(state, dict) else []
        if entries:
            target = str(entries[0].get("delete_commit_hash") or "").strip()

    if not target:
        return {
            "ok": False,
            "reason": "delete_commit_not_found",
            "error": "No undoable delete commit found",
        }

    rev_check = _git_run(["rev-parse", "--verify", target])
    if rev_check.returncode != 0:
        return {
            "ok": False,
            "reason": "invalid_commit",
            "error": rev_check.stderr.strip() or rev_check.stdout.strip(),
            "target": target,
        }

    revert_proc = _git_run(["revert", "--no-edit", target])
    if revert_proc.returncode != 0:
        return {
            "ok": False,
            "reason": "git_revert_failed",
            "error": revert_proc.stderr.strip() or revert_proc.stdout.strip(),
            "target": target,
        }

    head = _git_run(["rev-parse", "--short", "HEAD"])
    _remove_undo_entry(target)

    return {
        "ok": True,
        "reverted_commit": target,
        "new_commit": head.stdout.strip() if head.returncode == 0 else "",
    }


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

    def _read_json_body(self) -> dict:
        content_len = int(self.headers.get("Content-Length", "0"))
        if content_len <= 0:
            return {}
        raw = self.rfile.read(content_len)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        path = self._api_path()
        if path == "/api/notes":
            self._send_json(_load_notes())
            return
        if path == "/api/revert-delete-state":
            self._send_json(_load_undo_state())
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = self._api_path()
        if path == "/api/revert-delete":
            body = self._read_json_body()
            commit_hash = str(body.get("commit_hash") or "").strip()
            result = _git_revert_delete(commit_hash if commit_hash else None)
            status = HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST
            payload = {**result, "undo_state": _load_undo_state()}
            self._send_json(payload, status=status)
            return

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

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

        removed_file: Path | None = None
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
                removed_file = abs_md

        git_result = _git_autocommit_delete(
            note_id=note_id,
            note_title=str(target.get("title") or ""),
            removed_file=removed_file,
        )

        self._send_json(
            {
                "ok": True,
                "deleted_id": note_id,
                "remaining": len(notes),
                "removed_markdown_file": str(removed_file) if removed_file else None,
                "git": git_result,
                "undo_state": _load_undo_state(),
            }
        )


def main() -> None:
    global AUTO_GIT_COMMIT

    parser = argparse.ArgumentParser(description="Serve dashboard + notes API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument(
        "--no-auto-git-commit",
        action="store_true",
        help="Disable automatic git commit after deleting notes",
    )
    args = parser.parse_args()

    AUTO_GIT_COMMIT = not args.no_auto_git_commit

    os.chdir(ROOT)
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Serving {ROOT} on http://{args.host}:{args.port}")
    print(f"Auto git commit on delete: {'ON' if AUTO_GIT_COMMIT else 'OFF'}")
    print(f"Undo history limit: {UNDO_MAX_ENTRIES}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
