# Profa Eficientă / Proful Eficient

Profa Eficientă / Proful Eficient is an AI-powered educational platform designed to help mathematics teachers in Romania create, translate, and manage math exercises and exam materials. By utilizing generative artificial intelligence, the platform allows educators to transform natural language descriptions into properly formatted LaTeX expressions rendered instantly in the browser.

---

## Features

1.  **Teacher Assistant (Asistent AI)**: A chat interface helping teachers with mathematics pedagogy, lesson planning, and exercise generation.
2.  **Free Text to LaTeX Translation (Text → Mate)**: Translates Romanian math descriptions (e.g., *"integrala din x la patrat"*) into formatted equations. Includes options to generate step-by-step solutions or lists of similar exercises.
3.  **Document to LaTeX Generator (PDF/Docx → Mate)**: Extracts text from uploaded files (.pdf, .docx, .txt) and generates equivalent math equations or variations of the test paper.
4.  **Handwriting OCR (Scris de Mână → Digital)** (*Prototype*): A prototype designed to transcribe scanned handwritten worksheets into digital equations.
5.  **BAC Exam Generator (Generator BAC AI)** (*Prototype*): A prototype designed to generate custom Romanian Bacalaureat mock exam papers.

---

## Technology Stack

*   **Backend**: Python, Flask, Flask-Session
*   **Database**: SQLite
*   **AI Integration**: Google GenAI SDK (Gemini 2.5 Flash)
*   **Frontend**: Tailwind CSS, Bootstrap CSS, KaTeX (for mathematical rendering)

---

## Requirements

*   **Python**: Version 3.10 or higher
*   **Git**
*   **Gemini API Key**: A valid key from Google AI Studio

---

## Quick Start

Open PowerShell or Command Prompt and run the following commands to get the application running:

```powershell
git clone https://github.com/Eusebius33/Profa-Eficienta.git
cd Profa-Eficienta
python -m venv .venv
.venv\Scripts\Activate.ps1       # Use activate.bat on Command Prompt (CMD)
pip install -r requirements.txt
copy .env.example .env
# Open .env and add your GEMINI_API_KEY, then run:
python app.py
```

---

## Installation

### 1. Set Up the Environment
Create and activate your Python virtual environment, then install the dependencies:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> [!NOTE]  
> The initial package installation may take **10 to 20 minutes** depending on your network speed as it downloads deep learning frameworks required for document parsing.

### 2. Configure Environment Variables
Generate a local `.env` configuration file:
```powershell
copy .env.example .env
```
Open `.env` in a text editor and enter your key:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Start the Application
Run the main startup script:
```powershell
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser. The SQLite database is created and initialized automatically on startup.

---

## Project Structure

An overview of the main components of the codebase:

```text
Profa-Eficienta/
├── app.py                  # Main Flask server entry point
├── requirements.txt        # Python package dependencies
├── translations.json       # Localization keys for English and Romanian
├── test_gemini.py          # API validation script
├── secondary/              # Application modules
│   ├── accounts.py         # Registration, login, and style profiles
│   ├── adjacent.py         # Mode 2 math quick actions
│   ├── ai.py               # Gemini client setup and prompts
│   └── model_route.py      # Route logic for functional modes
├── templates/              # Jinja2 HTML templates
│   ├── apology.html        # Styled error page
│   └── modes/              # User interfaces for Modes 1-5
└── static/                 # Static styles and scripts
```

---

## Verification

To confirm your API key and AI connection are configured correctly without starting the web server, run the built-in validation script:

```powershell
python test_gemini.py
```

**Sample Output:**
```text
Checking environment variables...
GEMINI_API_KEY found: AQ.Ab...
Importing secondary.ai...
Testing translate_math function...
--- GEMINI RESPONSE ---
$$ (x^3)' $$
-----------------------
Test PASSED! Gemini API key is working successfully.
```

---

## Troubleshooting

*   **RuntimeError: AI nu este configurat.**:  
    Ensure you created the `.env` file in the root folder and configured a valid `GEMINI_API_KEY`.
*   **ModuleNotFoundError: No module named '...'**:  
    Verify that your virtual environment is active (indicated by `(.venv)` in your terminal prompt) and that you ran `pip install -r requirements.txt`.
*   **Database is Locked Errors**:  
    Ensure `profu.db` is not open in external database viewer tools while the Flask server is running.

---

## Current Limitations

*   **Mode 4 (Handwriting OCR)**: The frontend image upload input is not yet functional. The backend references a static mockup file.
*   **Mode 5 (BAC Generator)**: The lesson selection UI does not connect to the generation backend.
*   **Error Rendering**: The `apology.html` template must remain in the `templates/` directory to prevent system crashes when validation warnings occur.
