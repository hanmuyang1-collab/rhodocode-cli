"""Rhododendron backend connection constants and ~/.rhodocode config storage."""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SUPABASE_URL = "https://smtfunymjuvkvxgdplcn.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNtdGZ1bnltanV2a3Z4Z2RwbGNuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkwNDE0NDksImV4cCI6MjEwNDYxNzQ0OX0."
    "Cwmu-HNxuD4CksCQCB6rotwB4PhLYrFuwZU2oyL8vOk"
)

CONFIG_DIR = Path.home() / ".rhodocode"
CONFIG_PATH = CONFIG_DIR / "config.json"
MODELS_DIR = CONFIG_DIR / "models"

DEFAULTS: Dict[str, Any] = {
    "access_token": None,
    "refresh_token": None,
    "expires_at": 0,
    "email": None,
    "model": "deepseek-ai/deepseek-v4-flash-0731",
    "installed_models": [],
}


def load() -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text()))
        except Exception:
            pass
    # env overrides for CI / scripting
    if os.environ.get("RHODOCODE_TOKEN"):
        cfg["access_token"] = os.environ["RHODOCODE_TOKEN"]
    if os.environ.get("RHODOCODE_MODEL"):
        cfg["model"] = os.environ["RHODOCODE_MODEL"]
    return cfg


def save(cfg: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass


def update(**kwargs: Any) -> Dict[str, Any]:
    cfg = load()
    cfg.update(kwargs)
    save(cfg)
    return cfg


def clear_session() -> Dict[str, Any]:
    return update(access_token=None, refresh_token=None, expires_at=0, email=None)


def is_logged_in(cfg: Optional[Dict[str, Any]] = None) -> bool:
    cfg = cfg or load()
    return bool(cfg.get("access_token"))


def token_expired(cfg: Dict[str, Any]) -> bool:
    return time.time() > float(cfg.get("expires_at") or 0) - 30


def register_installed_model(hf_id: str, path: str) -> List[Dict[str, str]]:
    cfg = load()
    models: List[Dict[str, str]] = cfg.get("installed_models") or []
    models = [m for m in models if m.get("id") != hf_id]
    models.append({"id": hf_id, "path": path, "installed_at": int(time.time())})
    update(installed_models=models)
    return models
