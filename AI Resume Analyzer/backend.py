"""Backend logic for resume analysis with OpenAI and FastAPI."""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()


class ResumeAnalysisError(Exception):
    """Raised for analysis-related failures."""


class AnalysisRequest(BaseModel):
    resume_text: str = Field(..., min_length=30)
    job_role: str = Field(..., min_length=2, max_length=100)


def _build_prompt(resume_text: str, job_role: str) -> str:
    """Build a grounded prompt that enforces JSON output."""
    return f"""
You are an ATS and hiring expert.
Analyze the resume text ONLY based on content provided. Do not invent experience, education, projects, or skills.

Target job role: {job_role}

Return output as strict JSON with this schema:
{{
  "score": <integer from 0 to 100>,
  "score_breakdown": {{
    "keyword_match": <integer 0-100>,
    "experience_relevance": <integer 0-100>,
    "project_impact": <integer 0-100>,
    "formatting_clarity": <integer 0-100>
  }},
  "skills": ["..."],
  "missing_skills": ["..."],
  "suggestions": ["..."]
}}

Rules:
1) Skills must be explicitly present or strongly implied by resume content.
2) Missing skills must be relevant for the target role and absent in the resume.
3) Suggestions must be concrete and actionable (bullet-style short sentences).
4) Return only valid JSON. No markdown, no extra keys, no commentary.
5) Keep score_breakdown realistic and consistent with the resume evidence.

Resume text:
\"\"\"
{resume_text}
\"\"\"
""".strip()


def _normalize_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize potentially noisy model output into safe final structure."""
    score = payload.get("score", 0)
    if isinstance(score, str) and score.isdigit():
        score = int(score)
    if not isinstance(score, int):
        score = 0
    score = max(0, min(100, score))

    def normalize_sub_score(value: Any) -> int:
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        if not isinstance(value, int):
            return 0
        return max(0, min(100, value))

    def normalize_list(key: str) -> list[str]:
        value = payload.get(key, [])
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        normalized = [str(item).strip() for item in value if str(item).strip()]
        # Preserve order while removing duplicates.
        seen: set[str] = set()
        unique: list[str] = []
        for item in normalized:
            if item.lower() not in seen:
                seen.add(item.lower())
                unique.append(item)
        return unique

    breakdown_source = payload.get("score_breakdown", {})
    if not isinstance(breakdown_source, dict):
        breakdown_source = {}
    score_breakdown = {
        "keyword_match": normalize_sub_score(breakdown_source.get("keyword_match", score)),
        "experience_relevance": normalize_sub_score(breakdown_source.get("experience_relevance", score)),
        "project_impact": normalize_sub_score(breakdown_source.get("project_impact", score)),
        "formatting_clarity": normalize_sub_score(breakdown_source.get("formatting_clarity", score)),
    }

    return {
        "score": score,
        "score_breakdown": score_breakdown,
        "skills": normalize_list("skills"),
        "missing_skills": normalize_list("missing_skills"),
        "suggestions": normalize_list("suggestions"),
    }


def analyze_resume(resume_text: str, job_role: str, model: str = "gpt-4o-mini") -> dict[str, Any]:
    """Analyze resume text against a target role."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ResumeAnalysisError("OPENAI_API_KEY is not set. Add it to your environment.")

    if not resume_text or len(resume_text.strip()) < 30:
        raise ResumeAnalysisError("Resume text is too short to analyze.")
    if not job_role or len(job_role.strip()) < 2:
        raise ResumeAnalysisError("Please provide a valid job role.")

    client = OpenAI(api_key=api_key)
    prompt = _build_prompt(resume_text=resume_text.strip(), job_role=job_role.strip())

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
            temperature=0.2,
        )
        raw_output = response.output_text.strip()
    except Exception as exc:
        raise ResumeAnalysisError("Failed to get analysis from OpenAI API.") from exc

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        # Fallback if model wraps JSON in code fences.
        cleaned = raw_output.replace("```json", "").replace("```", "").strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ResumeAnalysisError("Model returned invalid JSON. Please try again.") from exc

    if not isinstance(parsed, dict):
        raise ResumeAnalysisError("Unexpected model output format.")

    analysis = _normalize_analysis(parsed)
    if not analysis["suggestions"]:
        analysis["suggestions"] = [
            "Add measurable impact to recent projects using numbers.",
            "Tailor your skills section to the target role keywords.",
        ]
    return analysis


app = FastAPI(title="AI Resume Analyzer API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
def analyze_endpoint(request: AnalysisRequest) -> dict[str, Any]:
    try:
        return analyze_resume(resume_text=request.resume_text, job_role=request.job_role)
    except ResumeAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
