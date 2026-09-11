"""Email/password auth against the Rhododendron Supabase backend."""

import time
from typing import Any, Dict, Optional

import requests

from . import config


class AuthError(Exception):
    pass


class AuthExpired(Exception):
    """Access token expired and refresh failed."""


def _token_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    grant = "refresh_token" if "refresh_token" in payload else "password"
    url = f"{config.SUPABASE_URL}/auth/v1/token?grant_type={grant}"
    r = requests.post(
        url,
        json=payload,
        headers={"apikey": config.ANON_KEY, "Content-Type": "application/json"},
        timeout=30,
    )
    if r.status_code != 200:
        try:
            msg = r.json().get("error_description") or r.json().get("msg") or r.text
        except Exception:
            msg = r.text
        raise AuthError(f"login failed ({r.status_code}): {msg}")
    return r.json()


def login(email: str, password: str) -> Dict[str, Any]:
    data = _token_request({"email": email, "password": password})
    return config.update(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=int(time.time()) + int(data.get("expires_in", 3600)),
        email=email,
    )


def refresh(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or config.load()
    rt = cfg.get("refresh_token")
    if not rt:
        raise AuthExpired("no refresh token — run `rhodocode login`")
    try:
        data = _token_request({"refresh_token": rt})
    except AuthError as e:
        raise AuthExpired(str(e)) from e
    return config.update(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", rt),
        expires_at=int(time.time()) + int(data.get("expires_in", 3600)),
    )


def get_token() -> str:
    """A valid access token, refreshing if needed."""
    cfg = config.load()
    if not cfg.get("access_token"):
        raise AuthError("not logged in — run `rhodocode login`")
    if config.token_expired(cfg):
        cfg = refresh(cfg)
    return cfg["access_token"]


def auth_headers(token: Optional[str] = None) -> Dict[str, str]:
    token = token or get_token()
    return {
        "Authorization": f"Bearer {token}",
        "apikey": config.ANON_KEY,
        "Content-Type": "application/json",
    }


def whoami() -> Optional[Dict[str, Any]]:
    cfg = config.load()
    if not cfg.get("access_token"):
        return None
    try:
        r = requests.get(
            f"{config.SUPABASE_URL}/auth/v1/user",
            headers=auth_headers(),
            timeout=20,
        )
        if r.status_code == 401:
            cfg = refresh(cfg)
            r = requests.get(
                f"{config.SUPABASE_URL}/auth/v1/user",
                headers=auth_headers(cfg["access_token"]),
                timeout=20,
            )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def profile() -> Optional[Dict[str, Any]]:
    """Tier / credits / dev_mode via the get_my_profile RPC."""
    try:
        r = requests.post(
            f"{config.SUPABASE_URL}/rest/v1/rpc/get_my_profile",
            headers=auth_headers(),
            json={},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        return data[0] if isinstance(data, list) and data else data
    except Exception:
        return None
