# AI Resume Analyzer (LLM Based)

AI Resume Analyzer is a production-ready web app that evaluates PDF resumes against a target job role using an LLM.

It provides:
- Resume score (0-100)
- ATS sub-scores (keyword match, experience relevance, project impact, formatting clarity)
- Extracted skills
- Missing skills for the selected role
- Actionable suggestions for improvement
- Export of analysis to JSON and CSV

## Tech Stack

- **Frontend:** Streamlit
- **Backend Logic/API:** Python + FastAPI
- **AI Engine:** OpenAI API (`gpt-4o-mini` by default)
- **PDF Parsing:** PyPDF2

## Project Structure

```text
/resume-analyzer
│── app.py
│── backend.py
│── utils.py
│── requirements.txt
│── README.md
```

## Prerequisites

- Python 3.10+
- OpenAI API key

## Setup

1. Clone or copy this folder locally.
2. (Recommended) Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set your OpenAI API key as an environment variable:

### Windows (PowerShell)
```powershell
$env:OPENAI_API_KEY="your_openai_api_key_here"
```

### macOS/Linux (bash/zsh)
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
```

Or copy `.env.example` to `.env` and set your key there for local development. The app auto-loads `.env` via `python-dotenv`.

## Run the Streamlit App

```bash
streamlit run app.py
```

Open the local URL shown in terminal (typically `http://localhost:8501`).

## Optional: Run FastAPI Endpoint

`backend.py` includes a FastAPI app with:
- `GET /health`
- `POST /analyze`

Run with:

```bash
uvicorn backend:app --reload
```

## How It Works

1. User uploads a PDF resume.
2. `utils.py` extracts and cleans text from PDF.
3. `backend.py` sends a structured prompt to OpenAI.
4. Model returns strict JSON:
   - `score`
   - `score_breakdown`
   - `skills`
   - `missing_skills`
   - `suggestions`
5. `app.py` displays results in a clean UI with score visualization and ATS sub-scores.
6. User can download analysis as JSON or CSV.

## Prompt Engineering Notes

The prompt is designed to:
- Force strict JSON output
- Restrict analysis to resume evidence only
- Reduce hallucinations by prohibiting invented details
- Provide role-specific missing skills and actionable recommendations

## Error Handling

The app handles:
- Missing file upload
- Empty/invalid PDF
- No extractable text
- Missing API key
- Invalid or malformed AI response

## Screenshots

- `[Placeholder] Home screen with upload + role input`
- `[Placeholder] Analysis output with score and skill sections`

## Production Notes

- Do not hardcode secrets; always use environment variables.
- Add request logging, authentication, and rate limiting before internet-facing deployment.
- Consider storing anonymized analysis results for observability and quality audits.
