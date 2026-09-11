# rhodocode 🌸

```
    * * *
  * o o *
    * * *
      |
     \|/
```

**Rhododendron Code** — an agentic coding assistant for the terminal, in the spirit of Claude Code, powered by the [Rhododendron](https://smtfunymjuvkvxgdplcn.supabase.co) multi-model backend. Its mascot is a cyan flower with white eyes, no mouth, no arrows.

It reads, writes, and edits your files, runs shell commands, searches your workspace, and iterates autonomously until the job is done — from your terminal, with the same account, models, credits, and developer mode as the Rhododendron web app.

## Install

```bash
pip install git+https://github.com/hanmuyang1-collab/rhodocode-cli.git

# with Hugging Face model-install support:
pip install "rhodocode[hf] @ git+https://github.com/hanmuyang1-collab/rhodocode-cli.git"
```

Requires Python 3.9+. The installed package and command are both called `rhodocode`.

## Quickstart

```bash
rhodocode login            # email + password from the Rhododendron web app
cd your-project
rhodocode                  # banner + interactive agent session
```

Then just tell it what to do:

```
rhodocode › add input validation to the signup form and run the tests
```

Or one-shot:

```bash
rhodocode agent "refactor utils.py to use pathlib, then run pytest"
```

## Commands

| Command | What it does |
|---|---|
| `rhodocode` | Banner + interactive agent REPL |
| `rhodocode agent "<task>"` | One-shot agentic coding run |
| `rhodocode chat "<prompt>"` | Plain chat with a model (no tools) |
| `rhodocode login` / `logout` / `whoami` | Account session |
| `rhodocode models` | List cloud + installed local models |
| `rhodocode use <model-id>` | Set the default model |
| `rhodocode install model <hf model> [token]` | Download a Hugging Face model into `~/.rhodocode/models` (token optional, for gated/private repos) |
| `rhodocode installed` | List locally installed models |
| `rhodocode credits` | Show remaining agent credits (∞ in developer mode) |
| `rhodocode config` | Show current configuration |
| `rhodocode version` / `--version` | Print version |

Chat/agent flags: `--model <id>`, `--thinking` / `--no-thinking`, `--effort low|medium|high|max`, `--max-tokens N`, `--max-steps N` (agent only).

Inside the agent REPL: `/model <id>` switches models mid-session; `exit` quits.

## Agent tools

The agent works inside your current directory with:

- `read_file`, `write_file`, `edit_file` (exact string replacement)
- `run_command` (shell, with timeout)
- `list_dir`, `search_files` (grep)

All paths are sandboxed to the workspace root. Destructive commands require your explicit instruction.

## Models

10 cloud models across free / pro / max tiers (DeepSeek V4 Flash & Pro, GPT-OSS 120B, Mistral Nemotron, Llama 3.2 90B Vision, MiniMax M3, Nemotron Nano Omni & 3 Ultra, Laguna XS 2.1, Kimi K3). Tier gating, credits, and developer mode are enforced by the Rhododendron backend — the same account you use on the web.

## Hugging Face models

```bash
rhodocode install model Qwen/Qwen2.5-Coder-7B-Instruct-GGUF
rhodocode install model meta-llama/Llama-3.1-8B-Instruct hf_xxxxxxxx   # gated model
```

Files land in `~/.rhodocode/models/` and are registered in the CLI config. After install, rhodocode prints run instructions (llama.cpp for GGUF, vLLM/transformers otherwise).

## Environment variables

- `RHODOCODE_TOKEN` — access token override (CI/scripts)
- `RHODOCODE_MODEL` — default model override

## License

MIT
