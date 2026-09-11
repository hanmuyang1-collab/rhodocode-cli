"""rhodocode CLI — command dispatch and interactive REPL."""

import argparse
import getpass
import sys
from typing import Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from . import __version__, agent, api, auth, config, install, mascot, models

console = Console()
CYAN = "bold cyan"


def _err(msg: str) -> int:
    console.print(f"[bold red]error:[/] {msg}")
    return 1


def _require_login() -> bool:
    if not config.is_logged_in():
        console.print("[yellow]not logged in.[/] Run [bold]rhodocode login[/] first.")
        return False
    return True


# ---------------------------------------------------------------- commands

def cmd_login(args) -> int:
    email = args.email or input("email: ").strip()
    password = args.password or getpass.getpass("password: ")
    try:
        cfg = auth.login(email, password)
    except auth.AuthError as e:
        return _err(str(e))
    console.print(f"{mascot.flower()}\n")
    console.print(f"[{CYAN}]logged in[/] as {cfg['email']}")
    prof = auth.profile()
    if prof:
        tier = prof.get("tier", "free")
        dev = " [magenta](developer mode ∞)[/]" if prof.get("dev_mode") else ""
        console.print(f"tier: [bold]{tier}[/]{dev} · credits: {prof.get('agent_credits', '?')}")
    return 0


def cmd_logout(args) -> int:
    config.clear_session()
    console.print(f"[{CYAN}]logged out[/]")
    return 0


def cmd_whoami(args) -> int:
    if not _require_login():
        return 1
    user = auth.whoami()
    prof = auth.profile()
    cfg = config.load()
    console.print(mascot.flower())
    console.print()
    if user:
        console.print(f"email:  [bold]{user.get('email', cfg.get('email'))}[/]")
    if prof:
        dev = " [magenta]∞ developer[/]" if prof.get("dev_mode") else ""
        console.print(f"tier:   [bold]{prof.get('tier', 'free')}[/]{dev}")
        console.print(f"credits: {prof.get('agent_credits', '?')}")
    console.print(f"model:  {cfg.get('model')}")
    return 0


def cmd_credits(args) -> int:
    if not _require_login():
        return 1
    prof = auth.profile()
    if not prof:
        return _err("could not fetch profile")
    if prof.get("dev_mode"):
        console.print("[magenta]∞ developer mode — unlimited credits[/]")
    else:
        console.print(
            f"credits: [bold]{prof.get('agent_credits', '?')}[/] "
            f"(tier: {prof.get('tier', 'free')})"
        )
    return 0


def cmd_models(args) -> int:
    cfg = config.load()
    current = cfg.get("model")
    table = Table(title="rhododendron cloud models", title_style=CYAN, border_style="cyan")
    table.add_column("id", style="cyan")
    table.add_column("label")
    table.add_column("tier")
    table.add_column("notes", style="dim")
    for m in models.MODELS:
        notes = []
        if m.get("reasoning"):
            notes.append("reasoning")
        if m.get("vision"):
            notes.append("vision")
        if m.get("efforts"):
            notes.append("effort: " + "/".join(m["efforts"]))
        mark = "● " if m["id"] == current else ""
        table.add_row(mark + m["id"], m["label"], m["tier"], ", ".join(notes))
    console.print(table)
    local = install.list_installed()
    if local:
        console.print("\n[bold]local models[/] (installed via `rhodocode install model`):")
        for lm in local:
            console.print(f"  [cyan]{lm['id']}[/] → [dim]{lm['path']}[/]")
    console.print("\nswitch with: [bold]rhodocode use <model-id>[/]")
    return 0


def cmd_use(args) -> int:
    m = models.find(args.model_id)
    if not m:
        return _err(f"unknown cloud model '{args.model_id}' — see `rhodocode models`")
    config.update(model=args.model_id)
    console.print(f"[{CYAN}]default model →[/] {m['label']} ([dim]{m['id']}[/])")
    return 0


def cmd_install(args) -> int:
    if args.what == "model":
        try:
            path = install.install_model(args.hf_model, args.token)
        except RuntimeError as e:
            return _err(str(e))
        except Exception as e:
            return _err(f"download failed: {e}")
        size = install.human_size(install.dir_size(path))
        console.print(f"[{CYAN}]installed[/] {args.hf_model} ({size})")
        console.print(install.run_hints(args.hf_model, path))
        return 0
    return _err(f"don't know how to install '{args.what}' — try: rhodocode install model <hf model> [token]")


def cmd_installed(args) -> int:
    local = install.list_installed()
    if not local:
        console.print("[dim]no local models yet. Install one with:[/] rhodocode install model <org/name> [token]")
        return 0
    table = Table(title="installed local models", title_style=CYAN, border_style="cyan")
    table.add_column("hugging face id", style="cyan")
    table.add_column("size")
    table.add_column("path", style="dim")
    from pathlib import Path
    for lm in local:
        table.add_row(lm["id"], install.human_size(install.dir_size(Path(lm["path"]))), lm["path"])
    console.print(table)
    return 0


def cmd_config(args) -> int:
    cfg = config.load()
    safe = {k: ("•••" if k.endswith("token") and v else v) for k, v in cfg.items()}
    console.print(f"[dim]{config.CONFIG_PATH}[/]")
    for k, v in safe.items():
        if k == "installed_models":
            console.print(f"  {k}: {len(v or [])} model(s)")
        else:
            console.print(f"  {k}: [cyan]{v}[/]")
    return 0


def _overrides(args) -> Dict:
    ov: Dict = {}
    if getattr(args, "thinking", None) is not None:
        ov["thinking"] = args.thinking
    if getattr(args, "effort", None):
        ov["effort"] = args.effort
    if getattr(args, "max_tokens", None):
        ov["max_tokens"] = args.max_tokens
    return ov


def cmd_chat(args) -> int:
    if not _require_login():
        return 1
    cfg = config.load()
    model = args.model or cfg["model"]
    prompt = " ".join(args.prompt) if args.prompt else None
    if not prompt:
        prompt = console.input(f"[{CYAN}]you ›[/] ")
    console.print(f"[dim]{model}[/]")
    out: List[str] = []
    try:
        api.stream_chat(
            model,
            [{"role": "user", "content": prompt}],
            on_delta=lambda d: (console.print(d, end=""), out.append(d)),
            overrides=_overrides(args),
        )
    except (api.ChatError, auth.AuthError) as e:
        return _err(str(e))
    console.print()
    return 0


def _agent_event_printer(e: agent.AgentEvent) -> None:
    if e.kind == "step":
        console.print(f"\n[dim]── step {e.data['n']} ──[/]")
    elif e.kind == "text":
        console.print(Markdown(e.data["text"]))
    elif e.kind == "tool":
        args = e.data["args"]
        brief = args.get("path") or args.get("command") or args.get("pattern") or ""
        console.print(f"[cyan]⚙ {e.data['name']}[/] [dim]{str(brief)[:90]}[/]")
    elif e.kind == "tool_result":
        out = e.data["output"]
        first = out.splitlines()[0] if out else ""
        style = "red" if out.startswith("error") else "dim"
        console.print(f"  [{style}]↳ {first[:120]}[/]")
    elif e.kind == "warn":
        console.print(f"[yellow]{e.data['text']}[/]")


def cmd_agent(args) -> int:
    if not _require_login():
        return 1
    cfg = config.load()
    model = args.model or cfg["model"]
    task = " ".join(args.task) if args.task else None
    history: List[Dict] = []

    console.print(mascot.flower())
    console.print(f"\n[dim]model:[/] [cyan]{model}[/] · [dim]workspace:[/] {__import__('os').getcwd()}")
    console.print("[dim]tools: read/write/edit files, run commands, list, search — type 'exit' to quit[/]\n")

    if task:  # one-shot
        try:
            agent.run_agent(model, task, on_event=_agent_event_printer,
                            overrides=_overrides(args), max_steps=args.max_steps)
        except (api.ChatError, auth.AuthError) as e:
            return _err(str(e))
        return 0

    while True:  # REPL
        try:
            task = console.input(f"[{CYAN}]rhodocode ›[/] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye 🌸[/]")
            return 0
        task = task.strip()
        if not task:
            continue
        if task.lower() in ("exit", "quit", ":q"):
            console.print("[dim]bye 🌸[/]")
            return 0
        if task.startswith("/model "):
            new = task.split(None, 1)[1].strip()
            if models.find(new):
                model = new
                config.update(model=new)
                console.print(f"[{CYAN}]model →[/] {new}")
            else:
                console.print("[red]unknown model[/] — see `rhodocode models`")
            continue
        try:
            final = agent.run_agent(
                model, task, history=history[-20:], on_event=_agent_event_printer,
                overrides=_overrides(args), max_steps=args.max_steps,
            )
            history.append({"role": "user", "content": task})
            if final:
                history.append({"role": "assistant", "content": final})
        except (api.ChatError, auth.AuthError) as e:
            _err(str(e))
        except KeyboardInterrupt:
            console.print("\n[yellow]interrupted[/]")


def cmd_version(args) -> int:
    console.print(mascot.flower())
    console.print(f"\nrhodocode v{__version__}")
    return 0


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rhodocode",
        description="Rhododendron Code — agentic coding assistant for the terminal. 🌸 (cyan flower, white eyes, no mouth, no arrows)",
    )
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("login", help="log in with your Rhododendron email + password")
    sp.add_argument("email", nargs="?")
    sp.add_argument("password", nargs="?")
    sp.set_defaults(fn=cmd_login)

    sp = sub.add_parser("logout", help="clear stored credentials")
    sp.set_defaults(fn=cmd_logout)

    sp = sub.add_parser("whoami", help="show account, tier, credits, current model")
    sp.set_defaults(fn=cmd_whoami)

    sp = sub.add_parser("credits", help="show remaining agent credits")
    sp.set_defaults(fn=cmd_credits)

    sp = sub.add_parser("models", help="list available cloud + installed local models")
    sp.set_defaults(fn=cmd_models)

    sp = sub.add_parser("use", help="set the default cloud model")
    sp.add_argument("model_id")
    sp.set_defaults(fn=cmd_use)

    sp = sub.add_parser("install", help="install things (currently: models from Hugging Face)")
    sp.add_argument("what", choices=["model"], help="what to install")
    sp.add_argument("hf_model", help="Hugging Face model id, e.g. Qwen/Qwen2.5-Coder-7B-Instruct-GGUF")
    sp.add_argument("token", nargs="?", default=None, help="Hugging Face access token (optional, for gated/private models)")
    sp.set_defaults(fn=cmd_install)

    sp = sub.add_parser("installed", help="list locally installed models")
    sp.set_defaults(fn=cmd_installed)

    sp = sub.add_parser("config", help="show current configuration")
    sp.set_defaults(fn=cmd_config)

    def add_chat_flags(sp):
        sp.add_argument("--model", "-m", help="override the model for this run")
        sp.add_argument("--thinking", action=argparse.BooleanOptionalAction, default=None,
                        help="toggle thinking mode (models that support it)")
        sp.add_argument("--effort", choices=["low", "medium", "high", "max"], help="reasoning effort")
        sp.add_argument("--max-tokens", type=int, dest="max_tokens")

    sp = sub.add_parser("chat", help="plain chat with a model (no tools)")
    sp.add_argument("prompt", nargs="*")
    add_chat_flags(sp)
    sp.set_defaults(fn=cmd_chat)

    sp = sub.add_parser("agent", help="agentic coding session (default command)")
    sp.add_argument("task", nargs="*")
    sp.add_argument("--max-steps", type=int, default=25, dest="max_steps")
    add_chat_flags(sp)
    sp.set_defaults(fn=cmd_agent)

    sp = sub.add_parser("version", help="print version")
    sp.set_defaults(fn=cmd_version)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        return cmd_version(args)
    fn = getattr(args, "fn", None)
    if fn is None:
        # bare `rhodocode` → banner + agent REPL
        return cmd_agent(argparse.Namespace(
            task=[], model=None, max_steps=25, thinking=None, effort=None, max_tokens=None,
        ))
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
