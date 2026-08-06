"""
Standalone diagnostic for the "AI works locally, blocked in prod" symptom.

Tests each configured Gemini API key INDIVIDUALLY and DIRECTLY — bypassing
this app's key-cycling manager (secondary/gemini_keys.py) entirely — so you
can see exactly which key(s) fail and why, plus the outbound IP this process
is actually calling Google from.

Usage: run it from wherever you suspect the block is happening. To check
whether Render itself is the problem, paste/run this from Render's Shell tab:

    python diagnose_gemini_keys.py

...and compare against running it locally. If a key fails here but works
locally with the exact same key, that's a strong signal Google is blocking
the request based on where it's coming from (common for free/no-billing
AI Studio keys called from a datacenter IP), not anything wrong in the code.
"""
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent))
load_dotenv()

from google import genai
from google.genai import types

from secondary import gemini_keys


def outbound_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as r:
            return r.read().decode().strip()
    except Exception as e:
        return f"(couldn't determine: {e})"


def main():
    print(f"Outbound IP this process is calling Google from: {outbound_ip()}\n")

    keys = gemini_keys.load_keys_from_env()
    if not keys:
        print("ERROR: no GEMINI_API_KEY_1..N (or GEMINI_API_KEY) found in environment.")
        sys.exit(1)

    print(f"Found {len(keys)} key(s) — testing each one individually and directly")
    print("(no cycling/fallback here, so you see exactly which key(s) fail and why):\n")

    any_ok = False
    for i, key in enumerate(keys, start=1):
        label = f"key {i} ({key[:6]}...{key[-4:]})"
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Say OK.",
                config=types.GenerateContentConfig(temperature=0),
            )
            print(f"[OK]   {label}: {response.text.strip()[:60]!r}")
            any_ok = True
        except Exception as e:
            blocked = gemini_keys.is_key_blocked_error(e)
            rate_limited = gemini_keys.is_rate_limit_error(e)
            reason = "BLOCKED" if blocked else "RATE LIMITED" if rate_limited else "OTHER ERROR"
            code = getattr(e, "code", "?")
            print(f"[FAIL] {label}: {reason} (code={code})")
            print(f"       {e}\n")

    print()
    if any_ok:
        print("At least one key worked from this environment.")
    else:
        print("Every key failed from this environment. If you're running this on")
        print("Render and the same keys work fine locally, it's very likely Google")
        print("blocking requests from Render's IP range for these specific keys")
        print("(common for free-tier/no-billing AI Studio keys) - not a code bug.")


if __name__ == "__main__":
    main()
