"""Filesystem tools scoped to a workspace root."""

from __future__ import annotations

import json
from pathlib import Path


def _resolve(workspace: Path, relative: str) -> Path:
    root = workspace.resolve()
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Path escapes workspace: {relative}")
    return target


def list_files(workspace: Path, path: str = ".") -> str:
    target = _resolve(workspace, path)
    if not target.is_dir():
        raise ValueError(f"Not a directory: {path}")
    entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    lines = [
        f"{'[dir]' if p.is_dir() else '[file]'} {p.relative_to(workspace.resolve()).as_posix()}"
        for p in entries
    ]
    return "\n".join(lines) if lines else "(empty directory)"


def read_file(workspace: Path, path: str) -> str:
    target = _resolve(workspace, path)
    if not target.is_file():
        raise ValueError(f"Not a file: {path}")
    return target.read_text(encoding="utf-8")


def write_file(workspace: Path, path: str, content: str) -> str:
    target = _resolve(workspace, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories under a path in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from workspace root. Defaults to '.'.",
                    }
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."}
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a text file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                    "content": {"type": "string", "description": "Full file contents."},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
]


def run_tool(workspace: Path, name: str, arguments: str) -> str:
    args = json.loads(arguments) if arguments else {}
    try:
        if name == "list_files":
            return list_files(workspace, args.get("path", "."))
        if name == "read_file":
            return read_file(workspace, args["path"])
        if name == "write_file":
            return write_file(workspace, args["path"], args["content"])
        return f"Unknown tool: {name}"
    except (KeyError, ValueError, OSError) as exc:
        return f"Error: {exc}"
