"""File upload route for text extraction."""
from __future__ import annotations

import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from autoquery.api.schemas.upload import UploadResponse

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_MIMES = {
    "text/plain": ".txt",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_WORDS = 2000

ALLOWED_CATEGORIES = {"query_letter", "synopsis", "manuscript_excerpt", "pitch_deck"}


def _extract_txt(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _extract_docx(data: bytes) -> str:
    import docx
    doc = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_pdf(data: bytes) -> str:
    import pdfplumber
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(...),
):
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid category. Allowed: {sorted(ALLOWED_CATEGORIES)}",
        )

    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Allowed: .txt, .pdf, .docx",
        )

    data = await file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_SIZE_BYTES // (1024*1024)} MB",
        )

    ext = ALLOWED_MIMES[content_type]
    if ext == ".txt":
        text = _extract_txt(data)
    elif ext == ".docx":
        text = _extract_docx(data)
    elif ext == ".pdf":
        text = _extract_pdf(data)
    else:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported")

    text = _truncate_words(text, MAX_WORDS)
    word_count = len(text.split())

    return UploadResponse(
        text=text,
        word_count=word_count,
        category=category,
        filename=file.filename or "unknown",
    )
