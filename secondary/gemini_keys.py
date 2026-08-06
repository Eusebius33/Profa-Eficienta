"""
Single active Gemini API key - no automatic cycling/failover between keys.

Only GEMINI_API_KEY_1 is used at runtime (GEMINI_API_KEY_2, then a bare
GEMINI_API_KEY, are read only as a startup fallback if _1 itself isn't set -
not as an automatic switch when a request fails). Any other numbered keys
still present in .env are ignored by the app; they were getting
API_KEY_SERVICE_BLOCKED from Google, and hammering already-blocked keys on
every request (the old round-robin-on-failure behavior) risked getting the
whole IP/account flagged instead of just failing gracefully.

If GEMINI_API_KEY_1 ever needs replacing, swap in GEMINI_API_KEY_2's value
and restart - this is a manual, deliberate action, not something the code
does for you.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

_PLACEHOLDER = "your_gemini_api_key_here"
_NUMBERED_KEY_RE = re.compile(r"^GEMINI_API_KEY_(\d+)$")


def load_keys_from_env():
    """Read every GEMINI_API_KEY_1..N (numeric order) plus a bare GEMINI_API_KEY
    fallback present in the environment. Diagnostic/manual-testing use only
    (see diagnose_gemini_keys.py, test_gemini.py) - the running app does not
    use this to pick which key to call, see _active_key() below."""
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


def _active_key():
    """The one key the app actually calls. GEMINI_API_KEY_1 first; _2 and the
    bare GEMINI_API_KEY are only consulted if _1 isn't configured at all."""
    for name in ("GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY"):
        value = os.getenv(name)
        if value and value != _PLACEHOLDER:
            return value
    return None


def is_rate_limit_error(error):
    code = getattr(error, "code", None)
    if code == 429:
        return True
    status = getattr(error, "status", "") or ""
    return "RESOURCE_EXHAUSTED" in str(status).upper()


def is_key_blocked_error(error):
    """A specific key/project is denied access (e.g. API_KEY_SERVICE_BLOCKED,
    API_KEY_INVALID, SERVICE_DISABLED) rather than just over quota."""
    code = getattr(error, "code", None)
    status = str(getattr(error, "status", "") or "").upper()
    text = str(error).upper()
    if code == 403 and ("PERMISSION_DENIED" in status or "PERMISSION_DENIED" in text):
        return True
    return any(marker in text for marker in (
        "API_KEY_SERVICE_BLOCKED", "API_KEY_INVALID", "SERVICE_DISABLED",
    ))


_client = None


def get_client():
    """Lazily build the single shared Gemini client (raises if no key is configured)."""
    global _client
    if _client is None:
        key = _active_key()
        if not key:
            raise RuntimeError(
                "AI nu este configurat. Adauga GEMINI_API_KEY_1 (si, optional, "
                "GEMINI_API_KEY_2 ca rezerva manuala) in fisierul .env."
            )
        _client = genai.Client(api_key=key)
    return _client
