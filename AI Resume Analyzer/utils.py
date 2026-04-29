"""Utility helpers for PDF parsing and text cleaning."""

from __future__ import annotations

from io import BytesIO
import re
from typing import BinaryIO

from PyPDF2 import PdfReader


class PDFProcessingError(Exception):
    """Raised when a PDF cannot be processed safely."""


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace while preserving paragraph boundaries."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(uploaded_file: BinaryIO) -> str:
    """Extract text content from an uploaded PDF-like object."""
    if uploaded_file is None:
        raise PDFProcessingError("No PDF file was provided.")

    try:
        file_bytes = uploaded_file.read()
        if not file_bytes:
            raise PDFProcessingError("The uploaded PDF is empty.")

        pdf_stream = BytesIO(file_bytes)
        reader = PdfReader(pdf_stream)
    except PDFProcessingError:
        raise
    except Exception as exc:
        raise PDFProcessingError("Could not read the PDF file. Please upload a valid PDF.") from exc
    finally:
        # Reset stream pointer for Streamlit UploadedFile reuse.
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

    if not reader.pages:
        raise PDFProcessingError("The PDF has no readable pages.")

    extracted_chunks: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            extracted_chunks.append(page_text)

    if not extracted_chunks:
        raise PDFProcessingError("No readable text found in the PDF.")

    cleaned_text = _normalize_whitespace("\n".join(extracted_chunks))
    if not cleaned_text:
        raise PDFProcessingError("Extracted text is empty after cleaning.")

    return cleaned_text
