import sys
import os

# Make the project root importable so `import app`, `from secondary import ...` work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402

# Vercel's Python runtime looks for a WSGI-compatible callable named `app`
