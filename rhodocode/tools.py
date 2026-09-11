"""Agent tools — file and shell operations sandboxed to the working directory."""

import os
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional

MAX_OUTPUT = 12000


def _resolve(path: str, root: Path) -> Path:
    """Resolve a user/agent-supplied path inside the workspace root."""
    p = (root / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        raise ValueError(f"path escapes workspace: {path}")
    return p


def _clip(text: str) -> str:
    if len(text) > MAX_OUTPUT:
        return text[:MAX_OUTPUT] + f"\n… [truncated, {len(text)} chars total]"
    return text


def tool_read_file(args: Dict, root: Path) -> str:
    p = _resolve(args["path"], root)
    if not p.is_file():
        return f"error: not a file: {args['path']}"
    try:
        return _clip(p.read_text(errors="replace"))
    except Exception as e:
        return f"error: {e}"


def tool_write_file(args: Dict, root: Path) -> str:
    p = _resolve(args["path"], root)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args.get("content", ""))
        return f"wrote {p.relative_to(root)} ({len(args.get('content', ''))} chars)"
    except Exception as e:
        return f"error: {e}"


def tool_edit_file(args: Dict, root: Path) -> str:
    p = _resolve(args["path"], root)
    if not p.is_file():
        return f"error: not a file: {args['path']}"
    old, new = args.get("old_string", ""), args.get("new_string", "")
    text = p.read_text(errors="replace")
    count = text.count(old)
    if count == 0:
        return "error: old_string not found"
    if count > 1 and not args.get("replace_all"):
        return f"error: old_string occurs {count} times — make it unique or set replace_all"
    p.write_text(text.replace(old, new) if args.get("replace_all") else text.replace(old, new, 1))
    return f"edited {p.relative_to(root)}"


def tool_run_command(args: Dict, root: Path) -> str:
    cmd = args["command"]
    timeout = min(int(args.get("timeout", 120)), 600)
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=root, capture_output=True, text=True, timeout=timeout
        )
        out = (proc.stdout or "") + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")
        return _clip(out or f"(exit {proc.returncode}, no output)") + f"\n[exit {proc.returncode}]"
    except subprocess.TimeoutExpired:
        return f"error: command timed out after {timeout}s"
    except Exception as e:
        return f"error: {e}"


def tool_list_dir(args: Dict, root: Path) -> str:
    p = _resolve(args.get("path", "."), root)
    if not p.is_dir():
        return f"error: not a directory: {args.get('path', '.')}"
    entries: List[str] = []
    try:
        for child in sorted(p.iterdir()):
            if child.name.startswith(".") and child.name not in (".github",):
                continue
            entries.append(("[dir] " if child.is_dir() else "      ") + child.name)
    except Exception as e:
        return f"error: {e}"
    return "\n".join(entries[:400]) or "(empty)"


def tool_search_files(args: Dict, root: Path) -> str:
    pattern = args["pattern"]
    path = args.get("path", ".")
    try:
        base = _resolve(path, root)
    except ValueError as e:
        return f"error: {e}"
    try:
        proc = subprocess.run(
            ["grep", "-rn", "--include=*", "-E", pattern, str(base)],
            capture_output=True, text=True, timeout=60,
        )
        out = proc.stdout.replace(str(root) + "/", "")
        return _clip(out) or "(no matches)"
    except FileNotFoundError:
        # fallback: pure python search
        hits: List[str] = []
        import re
        rx = re.compile(pattern)
        for f in base.rglob("*"):
            if f.is_file() and f.stat().st_size < 1_000_000:
                try:
                    for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                        if rx.search(line):
                            hits.append(f"{f.relative_to(root)}:{i}: {line.strip()[:200]}")
                except Exception:
                    continue
        return _clip("\n".join(hits)) or "(no matches)"
    except Exception as e:
        return f"error: {e}"


TOOLS: Dict[str, Callable[[Dict, Path], str]] = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    "run_command": tool_run_command,
    "list_dir": tool_list_dir,
    "search_files": tool_search_files,
}

TOOL_SPECS = """\
read_file      {"path": "relative/path"}                         — read a file's contents
write_file     {"path": "...", "content": "..."}                 — create/overwrite a file
edit_file      {"path": "...", "old_string": "...", "new_string": "..."}  — exact string replacement (add "replace_all": true for all)
run_command    {"command": "shell command", "timeout": 120}      — run a shell command in the workspace
list_dir       {"path": "."}                                     — list directory contents
search_files   {"pattern": "regex", "path": "."}                 — grep the workspace"""


def execute(name: str, args: Dict, root: Path) -> str:
    fn = TOOLS.get(name)
    if not fn:
        return f"error: unknown tool '{name}'. Available: {', '.join(TOOLS)}"
    try:
        return fn(args, root)
    except KeyError as e:
        return f"error: missing argument {e} for tool '{name}'"
    except Exception as e:
        return f"error in {name}: {e}"
