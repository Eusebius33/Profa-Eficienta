"""
Cycles through multiple Gemini API keys so free-tier per-key limits (e.g. ~20
requests/day) don't block the app. Keys live in .env as GEMINI_API_KEY_1 ..
GEMINI_API_KEY_10 (GEMINI_API_KEY alone still works for a single key).

When a key gets a 429/RESOURCE_EXHAUSTED response it is put on cooldown and
the manager moves on to the next available key.
"""

import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

_PLACEHOLDER = "your_gemini_api_key_here"
_NUMBERED_KEY_RE = re.compile(r"^GEMINI_API_KEY_(\d+)$")
_RETRY_DELAY_RE = re.compile(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)")

# Free-tier daily quotas reset ~24h after they're hit; used when the API
# doesn't tell us a more specific retryDelay (e.g. a per-minute burst limit).
DEFAULT_COOLDOWN = timedelta(hours=24)


def load_keys_from_env():
    """Read GEMINI_API_KEY_1..N (numeric order) plus a bare GEMINI_API_KEY fallback."""
    numbered = []
    for name, value in os.environ.items():
        match = _NUMBERED_KEY_RE.match(name)
        if match and value and value != _PLACEHOLDER:
            numbered.append((int(match.group(1)), value))
    numbered.sort(key=lambda pair: pair[0])
    keys = [value for _, value in numbered]

    single = os.getenv("GEMINI_API_KEY")
    if single and single != _PLACEHOLDER and single not in keys:
        keys.append(single)

    return keys


def is_rate_limit_error(error):
    code = getattr(error, "code", None)
    if code == 429:
        return True
    status = getattr(error, "status", "") or ""
    return "RESOURCE_EXHAUSTED" in str(status).upper()


def is_key_blocked_error(error):
    """A specific key/project is denied access (e.g. API_KEY_SERVICE_BLOCKED,
    API_KEY_INVALID, SERVICE_DISABLED) rather than just over quota. Unlike a
    rate limit this won't resolve itself, but the fix is the same either way:
    stop using this key and move on to the next one instead of surfacing the
    raw error to the user."""
    code = getattr(error, "code", None)
    status = str(getattr(error, "status", "") or "").upper()
    text = str(error).upper()
    if code == 403 and ("PERMISSION_DENIED" in status or "PERMISSION_DENIED" in text):
        return True
    return any(marker in text for marker in (
        "API_KEY_SERVICE_BLOCKED", "API_KEY_INVALID", "SERVICE_DISABLED",
    ))


def _retry_delay_seconds(error):
    details = getattr(error, "details", None)
    if not details:
        return None
    match = _RETRY_DELAY_RE.search(str(details))
    return int(match.group(1)) if match else None


class GeminiKeyManager:
    """Round-robins across Gemini API keys, skipping ones on cooldown."""

    def __init__(self, keys):
        if not keys:
            raise RuntimeError(
                "AI nu este configurat. Adauga GEMINI_API_KEY_1..GEMINI_API_KEY_10 "
                "(sau GEMINI_API_KEY) in fisierul .env."
            )
        self._keys = keys
        self._lock = threading.Lock()
        self._index = 0
        self._cooldowns = {}
        self._clients = {}

    def key_count(self):
        return len(self._keys)

    def _client_for(self, key):
        client = self._clients.get(key)
        if client is None:
            client = genai.Client(api_key=key)
            self._clients[key] = client
        return client

    def _available(self, key, now):
        until = self._cooldowns.get(key)
        return until is None or until <= now

    def current_client(self):
        """Client for the current key, skipping over any keys still on cooldown."""
        now = datetime.now(timezone.utc)
        with self._lock:
            for offset in range(len(self._keys)):
                idx = (self._index + offset) % len(self._keys)
                if self._available(self._keys[idx], now):
                    self._index = idx
                    return self._client_for(self._keys[idx])
            # Every key is on cooldown - use the current one anyway so the
            # caller gets a real error back instead of silently hanging.
            return self._client_for(self._keys[self._index])

    def mark_rate_limited(self, error=None):
        """Put the current key on cooldown and advance to the next one."""
        with self._lock:
            key = self._keys[self._index]
            retry_seconds = _retry_delay_seconds(error)
            cooldown = (
                timedelta(seconds=retry_seconds)
                if retry_seconds and retry_seconds < DEFAULT_COOLDOWN.total_seconds()
                else DEFAULT_COOLDOWN
            )
            self._cooldowns[key] = datetime.now(timezone.utc) + cooldown
            self._index = (self._index + 1) % len(self._keys)


_manager = None
_manager_lock = threading.Lock()


def get_manager():
    """Lazily build the process-wide key manager (raises if no keys are configured)."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = GeminiKeyManager(load_keys_from_env())
    return _manager
