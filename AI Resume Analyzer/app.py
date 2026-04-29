"""Streamlit frontend for AI Resume Analyzer."""

from __future__ import annotations

import csv
import io
import json

import streamlit as st

from backend import ResumeAnalysisError, analyze_resume
from utils import PDFProcessingError, extract_text_from_pdf


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
            .score-card {
                padding: 1rem;
                border-radius: 12px;
                border: 1px solid #2E8B57;
                background: #0f1720;
                margin-bottom: 1rem;
            }
            .section-card {
                padding: 1rem;
                border-radius: 10px;
                border: 1px solid #2f3640;
                margin-bottom: 0.75rem;
            }
            .section-title {
                font-weight: 700;
                margin-bottom: 0.3rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_list_section(title: str, items: list[str], empty_message: str) -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if items:
        for item in items:
            st.markdown(f"- {item}")
    else:
        st.write(empty_message)
    st.markdown("</div>", unsafe_allow_html=True)


def _build_csv_export(analysis: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "value"])
    writer.writerow(["score", analysis.get("score", 0)])

    breakdown = analysis.get("score_breakdown", {})
    for key in ["keyword_match", "experience_relevance", "project_impact", "formatting_clarity"]:
        writer.writerow([f"score_breakdown.{key}", breakdown.get(key, 0)])

    for item in analysis.get("skills", []):
        writer.writerow(["skills", item])
    for item in analysis.get("missing_skills", []):
        writer.writerow(["missing_skills", item])
    for item in analysis.get("suggestions", []):
        writer.writerow(["suggestions", item])
    return output.getvalue()


def main() -> None:
    st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄", layout="centered")
    _inject_styles()

    st.title("AI Resume Analyzer")
    st.caption("Upload a resume PDF, enter a role, and get AI-powered improvement suggestions.")

    uploaded_pdf = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
    job_role = st.text_input("Target Job Role", placeholder="e.g., AI Engineer")

    analyze_clicked = st.button("Analyze Resume", type="primary")
    if not analyze_clicked:
        return

    if uploaded_pdf is None:
        st.error("Please upload a PDF resume before analyzing.")
        return
    if not job_role.strip():
        st.error("Please enter a target job role.")
        return

    try:
        with st.spinner("Extracting resume text..."):
            resume_text = extract_text_from_pdf(uploaded_pdf)
    except PDFProcessingError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Unexpected PDF parsing error. Please try another file.")
        return

    try:
        with st.spinner("Running AI analysis..."):
            analysis = analyze_resume(resume_text=resume_text, job_role=job_role)
    except ResumeAnalysisError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Unexpected analysis error. Please try again.")
        return

    score = analysis.get("score", 0)
    st.markdown('<div class="score-card">', unsafe_allow_html=True)
    st.subheader(f"Resume Score: {score}/100")
    st.progress(int(score))
    st.markdown("</div>", unsafe_allow_html=True)

    breakdown = analysis.get("score_breakdown", {})
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Keyword Match", f"{breakdown.get('keyword_match', 0)}")
        st.metric("Project Impact", f"{breakdown.get('project_impact', 0)}")
    with col2:
        st.metric("Experience Relevance", f"{breakdown.get('experience_relevance', 0)}")
        st.metric("Formatting Clarity", f"{breakdown.get('formatting_clarity', 0)}")

    _render_list_section("Extracted Skills", analysis.get("skills", []), "No clear skills identified.")
    _render_list_section(
        "Missing Skills",
        analysis.get("missing_skills", []),
        "No critical missing skills detected for this role.",
    )
    _render_list_section(
        "Suggestions for Improvement",
        analysis.get("suggestions", []),
        "No suggestions returned. Try re-running analysis.",
    )

    st.subheader("Export Results")
    export_col1, export_col2 = st.columns(2)
    with export_col1:
        st.download_button(
            "Download JSON",
            data=json.dumps(analysis, indent=2),
            file_name="resume_analysis.json",
            mime="application/json",
        )
    with export_col2:
        st.download_button(
            "Download CSV",
            data=_build_csv_export(analysis),
            file_name="resume_analysis.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
