"""
User-uploaded file handling.

Design: like Claude's own file handling, this does NOT persist
uploaded documents to disk/ChromaDB/GCS. Extracted text is kept
in-memory for the lifetime of the conversation only, capped at
MAX_CONTEXT_CHARS so it stays within what the model can hold in
context. Static/shared FAQ data (a separate, persistent dataset)
is handled by embed.py with GCS-backed ChromaDB instead - that's
a different kind of data with different persistence needs.
"""

import io
import fitz  # pymupdf
import docx
import pandas as pd
from pptx import Presentation

MAX_CONTEXT_CHARS = 8000  # keep extracted text within what fits comfortably in context


def _from_pdf(content):
    doc = fitz.open(stream=content, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

def _from_docx(content):
    d = docx.Document(io.BytesIO(content))
    return "\n".join(p.text for p in d.paragraphs)

def _from_csv(content):
    df = pd.read_csv(io.BytesIO(content))
    return df.to_string(index=False)

def _from_txt(content):
    return content.decode("utf-8", errors="ignore")

def _from_pptx(content):
    prs = Presentation(io.BytesIO(content))
    lines = [
        shape.text_frame.text
        for slide in prs.slides
        for shape in slide.shapes
        if shape.has_text_frame
    ]
    return "\n".join(lines)


EXTRACTORS = {
    "pdf": _from_pdf,
    "docx": _from_docx,
    "csv": _from_csv,
    "txt": _from_txt,
    "pptx": _from_pptx,
}


def extract_text(filename, content):
    ext = filename.lower().split(".")[-1]
    extractor = EXTRACTORS.get(ext)
    if not extractor:
        return None
    text = extractor(content).strip()
    return text[:MAX_CONTEXT_CHARS]