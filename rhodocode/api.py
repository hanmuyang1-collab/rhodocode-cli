"""Streaming + non-streaming chat against the Rhododendron chat edge function."""

import json
from typing import Callable, Dict, List, Optional

import requests

from . import auth, config

CHAT_URL = f"{config.SUPABASE_URL}/functions/v1/chat"


class ChatError(Exception):
    pass


def stream_chat(
    model: str,
    messages: List[Dict],
    on_delta: Callable[[str], None],
    overrides: Optional[Dict] = None,
    timeout: int = 240,
) -> str:
    """Stream a completion, calling on_delta(text) per chunk. Returns full text."""
    body: Dict = {"model": model, "messages": messages, "stream": True}
    if overrides:
        body.update({k: v for k, v in overrides.items() if v is not None})
    token = auth.get_token()
    full: List[str] = []
    with requests.post(
        CHAT_URL,
        json=body,
        headers=auth.auth_headers(token),
        stream=True,
        timeout=(15, timeout),
    ) as r:
        if r.status_code == 401:
            token = auth.refresh()["access_token"]
            return stream_chat(model, messages, on_delta, overrides, timeout)
        if r.status_code != 200:
            raise ChatError(f"chat failed ({r.status_code}): {r.text[:400]}")
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            if chunk.get("error"):
                raise ChatError(str(chunk["error"]))
            choices = chunk.get("choices") or [{}]
            delta = (choices[0].get("delta") or {}).get("content")
            if delta:
                full.append(delta)
                on_delta(delta)
    return "".join(full)


def complete_chat(
    model: str,
    messages: List[Dict],
    overrides: Optional[Dict] = None,
    timeout: int = 240,
) -> str:
    """One-shot (non-streaming) completion. Returns full text."""
    body: Dict = {"model": model, "messages": messages, "stream": False}
    if overrides:
        body.update({k: v for k, v in overrides.items() if v is not None})
    token = auth.get_token()
    r = requests.post(
        CHAT_URL,
        json=body,
        headers=auth.auth_headers(token),
        timeout=(15, timeout),
    )
    if r.status_code == 401:
        token = auth.refresh()["access_token"]
        r = requests.post(
            CHAT_URL, json=body, headers=auth.auth_headers(token), timeout=(15, timeout)
        )
    if r.status_code != 200:
        raise ChatError(f"chat failed ({r.status_code}): {r.text[:400]}")
    data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ChatError(f"unexpected chat response: {str(data)[:400]}") from e


def spend_credits(amount: int, reason: str) -> bool:
    """Best-effort credit metering, same RPC as the web app. Never raises."""
    try:
        r = requests.post(
            f"{config.SUPABASE_URL}/rest/v1/rpc/spend_credits",
            headers=auth.auth_headers(),
            json={"amount": amount, "reason": reason},
            timeout=15,
        )
        if r.status_code != 200:
            return True  # don't block the user on metering errors
        return bool(r.json())
    except Exception:
        return True
