# Profa Eficientă / Proful Eficient

#### Video Demo: https://youtu.be/1Zd5Qe2J454


#### Description
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
*   **Database**: PostgreSQL, via SQLAlchemy ORM (`models.py`)
*   **AI Integration**: Google GenAI SDK (Gemini 2.5 Flash)
*   **Frontend**: Tailwind CSS, Bootstrap CSS, KaTeX (for mathematical rendering)

---

## Requirements

*   **Git**
*   **Gemini API Key**: A valid key from Google AI Studio
*   Either:
    *   **Docker** + **Docker Compose** (recommended — no local Python/Postgres install needed), **or**
    *   **Python 3.13** and a **PostgreSQL server** you can connect to (local install, or someone else's instance)

---

## Quick Start (Docker — recommended)

```bash
git clone https://github.com/Eusebius33/Profa-Eficienta.git
cd Profa-Eficienta
cp .env.example .env
# Open .env and set GEMINI_API_KEY, SECRET_KEY, and (optionally) POSTGRES_PASSWORD, then:
docker compose up --build
```
Open **[http://localhost:8000](http://localhost:8000)**. Postgres runs in its own container and the app creates its schema automatically on first boot — nothing else to install. Data persists in Docker volumes across `docker compose down`/`up` (use `docker compose down -v` to wipe it).

## Quick Start (native, no Docker)

Open PowerShell or Command Prompt and run the following commands to get the application running:

```powershell
git clone https://github.com/Eusebius33/Profa-Eficienta.git
cd Profa-Eficienta
python -m venv .venv
.venv\Scripts\Activate.ps1       # Use activate.bat on Command Prompt (CMD)
pip install -r requirements.txt
copy .env.example .env
# Open .env: add your GEMINI_API_KEY, generate a SECRET_KEY, and point
# DATABASE_URL at a Postgres server you have (see step 2 below), then run:
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

### 2. Set Up PostgreSQL
The app needs a reachable Postgres server — pick one:
*   **Docker, Postgres only**: `docker compose up db` starts just the database container (useful if you want to run Flask natively for faster iteration but don't want to install Postgres yourself). It listens on `localhost:5432` with the credentials from your `.env`.
*   **Local install**: install PostgreSQL yourself and create a database (e.g. `profu_db`).
*   **Someone else's instance**: any reachable Postgres works.

No migration tool is needed — the app creates all its tables automatically on first run (`init_db()` in `app.py`, `Base.metadata.create_all()` in `models.py`).

### 3. Configure Environment Variables
Generate a local `.env` configuration file:
```powershell
copy .env.example .env
```
Open `.env` in a text editor and fill in:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=any_long_random_string
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/profu_db
```
`DATABASE_URL` must match whatever Postgres you set up in step 2. `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` have working defaults (5/10) — only change them if you know you need to.

### 4. Start the Application
Run the main startup script:
```powershell
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser.

---

## Project Structure

An overview of the main components of the codebase:

```text
Profa-Eficienta/
├── app.py                  # Main Flask server entry point
├── models.py                # SQLAlchemy engine/session + ORM models (Postgres)
├── requirements.txt        # Python package dependencies
├── Dockerfile                # App container image
├── docker-compose.yml        # App + Postgres, for local/containerized runs
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

## BAC Exam Generator (Mode 5)

The BAC Exam Generator is a fully programmatic, production-ready system that constructs unique mock exams following the official Romanian national "M_tehnologic" format.

### How it works:
1. **Selection & Randomization**: For each of the 10 exam slots, the generator picks from multiple pre-defined templates (Algebra, Geometry, Matrices, Composition Laws, Differential and Integral Calculus) and randomizes their parameters (coefficients, constants, equations).
2. **Custom Lesson Filtering**: The teacher can select specific lessons in the sidebar. The generator adapts the variants generated to target only the requested topics.
3. **Verification Pipeline**: Each generated exercise is dynamically checked against division-by-zero, negative square root arguments, non-positive logarithm base/arguments, and singular matrices to ensure mathematical correctness.
4. **Duplicate Prevention**: The system normalized the exercise texts (replacing variables and constants with `[NUM]` tokens), hashes the templates, and calculates the similarity index across current and past exams to guarantee that no duplicate exams are produced.
5. **A4 PDF Compilation**: Using ReportLab, the platform produces print-ready A4 PDFs for both the Student exam sheet and the Teacher sheet (complete with step-by-step solutions / barem), using standard TrueType fonts for complete Romanian diacritics support.

---

## Verification

To confirm your API key and AI connection are configured correctly without starting the web server, run the built-in validation script:

```powershell
python test_gemini.py
```

To run the automated tests for the BAC Exam Generator, execute:

```powershell
python -m unittest tests/test_bac_generator.py
```

---

## Troubleshooting

*   **RuntimeError: AI nu este configurat.**:  
    Ensure you created the `.env` file in the root folder and configured a valid `GEMINI_API_KEY`.
*   **ModuleNotFoundError: No module named '...'**:  
    Verify that your virtual environment is active (indicated by `(.venv)` in your terminal prompt) and that you ran `pip install -r requirements.txt`.
*   **RuntimeError: DATABASE_URL nu este setat.**:  
    You're running natively (no Docker) and `.env` is missing `DATABASE_URL`, or `.env` doesn't exist yet — copy it from `.env.example` and point it at a Postgres server you have running (see Installation, step 2).
*   **`could not connect to server` / connection refused (native run)**:  
    Postgres isn't reachable at the host/port in `DATABASE_URL`. If you meant to use the Docker Postgres, either run the whole stack with `docker compose up`, or just the database with `docker compose up db` while running Flask natively.
*   **`docker compose up` — `web` keeps restarting / can't reach `db`**:  
    Check `docker compose logs db` — the `web` service waits for Postgres's healthcheck before starting, so if `db` never becomes healthy, `web` won't start either. Also confirm `.env` exists (copied from `.env.example`); Compose reads it directly for `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`.

---

## Current Limitations

*   **Mode 4 (Handwriting OCR)**: The frontend image upload input is not yet functional. The backend references a static mockup file.
*   **Error Rendering**: The `apology.html` template must remain in the `templates/` directory to prevent system crashes when validation warnings occur.

