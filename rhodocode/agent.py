"""The rhodocode agent loop — parse ```tool blocks, execute, iterate. Like Claude Code, but flowery."""

import json
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import api, tools

TOOL_BLOCK = re.compile(r"```tool\s*\n(.*?)```", re.DOTALL)

SYSTEM = """\
You are Rhodocode, an agentic coding assistant running in the user's terminal, \
part of the Rhododendron multi-model platform. You work on the files in the user's \
current directory — reading, writing, editing, searching, and running commands to \
get real work done, autonomously.

## How to call tools
Emit one or more fenced tool blocks, then STOP and wait for results:

```tool
{"tool": "read_file", "args": {"path": "src/main.py"}}
```

Available tools:
%s

## Operating principles
1. Explore before editing: list_dir / read_file / search_files first, then act.
2. Make real changes with write_file / edit_file — don't just describe them.
3. Verify your work: run tests, builds, or the program itself with run_command.
4. One task at a time, but chain steps autonomously — don't stop to ask unless truly blocked.
5. Paths are relative to the workspace root (the user's current directory).
6. When the task is complete, reply with a concise summary and NO tool blocks.
7. Never run destructive commands (rm -rf, force pushes, dropping tables) unless the user explicitly asked.
""" % tools.TOOL_SPECS


def parse_tool_calls(text: str) -> List[Dict]:
    calls: List[Dict] = []
    for block in TOOL_BLOCK.findall(text):
        try:
            obj = json.loads(block.strip())
            if isinstance(obj, dict) and "tool" in obj:
                calls.append(obj)
        except json.JSONDecodeError:
            calls.append({"tool": "__parse_error__", "args": {"raw": block.strip()[:300]}})
    return calls


def strip_tool_blocks(text: str) -> str:
    return TOOL_BLOCK.sub("", text).strip()


class AgentEvent:
    def __init__(self, kind: str, **kw):
        self.kind = kind
        self.data = kw


def run_agent(
    model: str,
    task: str,
    history: Optional[List[Dict]] = None,
    max_steps: int = 25,
    on_event: Optional[Callable[[AgentEvent], None]] = None,
    overrides: Optional[Dict] = None,
    meter: bool = True,
) -> str:
    """Run the agent loop. Returns the final assistant text."""
    root = Path.cwd()
    messages: List[Dict] = [{"role": "system", "content": SYSTEM}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": task})

    emit = on_event or (lambda e: None)
    final_text = ""

    for step in range(1, max_steps + 1):
        emit(AgentEvent("step", n=step))
        text = api.complete_chat(model, messages, overrides=overrides)
        if meter:
            api.spend_credits(1, "cli_agent_step")
        messages.append({"role": "assistant", "content": text})

        calls = parse_tool_calls(text)
        visible = strip_tool_blocks(text)
        if visible:
            emit(AgentEvent("text", text=visible))

        if not calls:
            final_text = visible
            break

        results: List[str] = []
        for call in calls:
            name, args = call.get("tool", ""), call.get("args") or {}
            if name == "__parse_error__":
                out = f"error: could not parse tool JSON: {args.get('raw')}"
            else:
                emit(AgentEvent("tool", name=name, args=args))
                out = tools.execute(name, args, root)
            emit(AgentEvent("tool_result", name=name, output=out[:600]))
            results.append(f"[tool result: {name}]\n{out}")
        messages.append({"role": "user", "content": "\n\n".join(results)})
    else:
        emit(AgentEvent("warn", text=f"hit step budget ({max_steps})"))

    return final_text
