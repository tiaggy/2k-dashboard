"""Lightweight, independent reachability checks for the dashboard's own
header status indicators. Separate from (and faster than) the full
attendance-data refresh loop — whether Notion/AI are reachable right now is
a more time-sensitive signal than the slow Capture Log pull, and shouldn't
have to wait behind it.
"""
from __future__ import annotations

import requests

import config
import notion


def check_notion() -> str:
    """'ok' | 'down' | 'unconfigured'."""
    if not config.NOTION_ENABLED:
        return "unconfigured"
    try:
        return "ok" if notion.healthcheck() else "down"
    except Exception:
        return "down"


def check_ai() -> str:
    """'ok' | 'down' | 'unconfigured'. A cheap reachability probe (list
    models) — not an actual completion, so it costs nothing on a metered
    API. Same base-url convention as the bot's own classifier.py (which
    uses the official openai SDK): an unset OPENAI_BASE_URL means
    api.openai.com."""
    if not config.OPENAI_API_KEY:
        return "unconfigured"
    base = (config.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    try:
        r = requests.get(f"{base}/models", headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"}, timeout=8)
        # 401/403 means the endpoint answered but the key's bad — that's a
        # real, distinct problem, but "the endpoint itself is reachable" is
        # what this indicator is about, so still 'ok'. Only a hard failure
        # (timeout, connection error, 5xx) counts as 'down'.
        return "ok" if r.status_code < 500 else "down"
    except Exception:
        return "down"
