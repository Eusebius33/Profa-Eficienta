import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Load .env
load_dotenv()

print("Checking environment variables...")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY not found in environment!")
    sys.exit(1)
print(f"GEMINI_API_KEY found: {api_key[:5]}...{api_key[-5:] if len(api_key) > 5 else ''}")

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
