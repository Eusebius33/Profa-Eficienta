import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Load .env
load_dotenv()

print("Checking environment variables...")
from secondary import gemini_keys

keys = gemini_keys.load_keys_from_env()
if not keys:
    print("ERROR: No GEMINI_API_KEY_1..N (or GEMINI_API_KEY) found in environment!")
    sys.exit(1)
print(f"Found {len(keys)} Gemini API key(s):")
for i, key in enumerate(keys, start=1):
    print(f"  {i}. {key[:5]}...{key[-5:] if len(key) > 5 else ''}")

try:
    print("\nImporting secondary.ai...")
    from secondary import ai
    
    print("\nTesting translate_math function...")
    prompt = "derivata din x la a treia"
    style = "Explicatii clare"
    school_class = "Clasa a XI-a"
    bac = "M1"
    
    response = ai.translate_math(prompt, style, school_class, bac)
    print("\n--- GEMINI RESPONSE ---")
    print(response)
    print("-----------------------")
    
    if "Eroare AI" in response:
        print("\nTest FAILED with AI error.")
    else:
        print("\nTest PASSED! Gemini API key is working successfully.")
        
except Exception as e:
    print(f"\nERROR: Exception occurred during test: {e}")
    import traceback
    traceback.print_exc()
