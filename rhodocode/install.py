"""Install models from Hugging Face: `rhodocode install model <hf model> [token]`."""

import time
from pathlib import Path
from typing import List, Optional

from rich.progress import Progress, SpinnerColumn, TextColumn

from . import config


def install_model(hf_id: str, token: Optional[str] = None) -> Path:
    """Download a Hugging Face model into ~/.rhodocode/models and register it."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        raise RuntimeError(
            "huggingface-hub is required for model installs.\n"
            "Run: pip install 'rhodocode[hf]'   (or: pip install huggingface-hub)"
        )

    safe = hf_id.replace("/", "--")
    dest = config.MODELS_DIR / safe
    dest.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[cyan]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(f"downloading {hf_id} …", total=None)
        path = snapshot_download(
            repo_id=hf_id,
            token=token or None,
            local_dir=str(dest),
        )
    config.register_installed_model(hf_id, path)
    return Path(path)


def list_installed() -> List[dict]:
    return config.load().get("installed_models") or []


def dir_size(path: Path) -> int:
    total = 0
    try:
        for f in Path(path).rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except Exception:
        pass
    return total


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{n} B"


def run_hints(hf_id: str, path: Path) -> str:
    """Honest guidance on how to actually run an installed model."""
    ggufs = list(Path(path).rglob("*.gguf"))
    lines = [f"model files are at: {path}"]
    if ggufs:
        lines.append(
            "GGUF detected — run it with llama.cpp, e.g.:\n"
            f"  llama-server -m {ggufs[0]} --port 8080"
        )
    else:
        lines.append(
            "Transformers weights — serve them with vLLM or transformers, e.g.:\n"
            f"  python -m vllm.entrypoints.openai.api_server --model {hf_id}\n"
            "or load directly with `AutoModelForCausalLM.from_pretrained("
            f"'{hf_id}')`."
        )
    lines.append(f"installed at {time.strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)
