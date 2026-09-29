# isItCandidate | On-Premise AI Screening & Match Studio

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B.svg)](https://streamlit.io/)
[![Ollama](https://img.shields.io/badge/Ollama-Qwen%202.5%3A14B-black.svg)](https://ollama.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-336791.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Privacy First](https://img.shields.io/badge/Privacy-100%25%20On--Premise-teal.svg)](#)

> **isItCandidate** is a privacy-first, enterprise-grade AI Applicant Tracking System (ATS) and candidate matching studio. Powered by local LLMs (Ollama with Qwen 2.5:14B) and backed by PostgreSQL / SQLite, it evaluates CVs against custom job descriptions, technical requirements, and strict company policies without sending sensitive resume data to external cloud APIs.

---

## Key Features

- **100% On-Premise & Privacy-First (KVKK / GDPR Compliant):** All resume parsing and AI inferences execute entirely on your local machine using Ollama. Zero candidate data leaks to third-party cloud servers.
- **Strict Policy Gate:** Unlike simple keyword-matching engines, isItCandidate verifies non-negotiable operational requirements (e.g., hybrid/office attendance, relocation, military status, language certifications) and flags policy violations immediately.
- **Deterministic Multi-Criteria Evaluation:** Generates a structured 0-100 compatibility score, ATS keyword matching, missing technical gaps, executive summary, and tailored candidate-specific interview questions.
- **Hybrid RDBMS Architecture (PostgreSQL + SQLite Fallback):**
  - **PostgreSQL 18:** Indexed relational schema for high-performance querying and candidate archiving.
  - **SQLite Zero-Config Fallback:** Automatically switches to SQLite if PostgreSQL is not running, ensuring portability across environments.
- **Talent Pool & ATS Lifecycle Management:** Search candidates with SQL `ILIKE`, filter by status or score, track recruitment stages (*New Application, Passed Screening, Interview Scheduled, Offer Extended, Hired, Rejected*), and maintain recruiter notes.
- **Executive UI (TealHQ-Inspired):** Clean, professional dark-mode design built with Plus Jakarta Sans and JetBrains Mono typography, completely free of emojis, featuring candidate score gauges and CSV export.

---

## Architecture

```
[ Candidate CVs (PDF / TXT) ] + [ Job Description & Policies ]
                          │
                          ▼
         ┌─────────────────────────────────┐
         │ 1. Text Ingestion (pypdf/txt)   │
         └─────────────────────────────────┘
                          │ (Extracted Text)
                          ▼
         ┌─────────────────────────────────┐
         │ 2. Local AI Screening Engine    │
         │    (Ollama · Qwen 2.5:14B)      │
         │    - Policy Gate Audit          │
         │    - Skill Gap Detection        │
         │    - Tailored Interview Qs      │
         └─────────────────────────────────┘
                          │ (Structured JSON)
                          ▼
    ┌───────────────────────────────────────────┐
    │ 3. Database Layer (db_manager.py)         │
    │    PostgreSQL 18 · SQLite Fallback        │
    └───────────────────────────────────────────┘
                          │
                          ▼
    ┌───────────────────────────────────────────┐
    │ 4. Executive Studio (app.py)              │
    │    - Split Studio (Criteria & Matcher)    │
    │    - Talent Pool Search & Lifecycle       │
    └───────────────────────────────────────────┘
```

---

## Quick Start

### 1. Prerequisites

- **Python 3.10+** installed
- **Ollama** installed: [ollama.com](https://ollama.com)
  - Pull the model:
    ```bash
    ollama pull qwen2.5:14b
    ```
- **PostgreSQL (Optional):** If PostgreSQL is not installed, the app automatically defaults to local SQLite (`candidates_pool.db`).

### 2. Installation

Clone this repository and create a virtual environment:

```bash
git clone https://github.com/your-username/isItCandidate.git
cd isItCandidate

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Running the Application

Launch the Streamlit portal:

```bash
streamlit run app.py
```

The web studio will open at `http://localhost:8501`.

---

## Testing with Sample Portfolios

Click the **"Örnek Portföyü Yükle (3 Aday)"** button in the studio to immediately test the pipeline using 3 realistic resumes included in `ornek_cvler/`:
- `Mert Yılmaz` (Senior Python / FastAPI candidate)
- `Caner Özkan` (Mid-level Backend candidate)
- `Selin Demir` (Junior Frontend candidate)

---

## Project Structure

```
isItCandidate/
├── app.py                   # Main Streamlit web application & UI
├── cv_screening_engine.py   # Ollama LLM integration & prompt pipeline
├── db_manager.py            # PostgreSQL & SQLite hybrid database manager
├── start_postgres.bat       # Convenience batch launcher for local PostgreSQL
├── requirements.txt         # Production dependencies
├── .env.example             # Example environment configuration
├── .gitignore               # Ignored files (venv, logs, db)
├── LICENSE                  # MIT License
├── README.md                # Project documentation
└── ornek_cvler/             # Sample resumes for instant demonstration
    ├── Caner_Ozkan_Mid_Backend.txt
    ├── Mert_Yilmaz_Senior_Python.txt
    └── Selin_Demir_Junior_Frontend.txt
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
