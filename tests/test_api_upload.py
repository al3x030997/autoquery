"""Tests for file upload routes."""
import io
from unittest.mock import patch, MagicMock

import pytest


def test_upload_txt(client):
    content = b"This is a test document with some words in it."
    resp = client.post(
        "/api/upload",
        files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
        data={"category": "query_letter"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["word_count"] > 0
    assert data["category"] == "query_letter"
    assert data["filename"] == "test.txt"
    assert "test document" in data["text"]


def test_upload_docx(client):
    mock_doc = MagicMock()
    mock_para = MagicMock()
    mock_para.text = "Hello from docx"
    mock_doc.paragraphs = [mock_para]

    with patch("docx.Document", return_value=mock_doc):
        content = b"fake docx bytes"
        resp = client.post(
            "/api/upload",
            files={"file": ("test.docx", io.BytesIO(content),
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"category": "synopsis"},
        )
    assert resp.status_code == 200
    assert resp.json()["text"] == "Hello from docx"


def test_upload_pdf(client):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Hello from PDF"
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = lambda s: s
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch("pdfplumber.open", return_value=mock_pdf):
        content = b"fake pdf bytes"
        resp = client.post(
            "/api/upload",
            files={"file": ("test.pdf", io.BytesIO(content), "application/pdf")},
            data={"category": "manuscript_excerpt"},
        )
    assert resp.status_code == 200
    assert resp.json()["text"] == "Hello from PDF"


def test_upload_rejects_exe(client):
    resp = client.post(
        "/api/upload",
        files={"file": ("malware.exe", io.BytesIO(b"evil"), "application/octet-stream")},
        data={"category": "query_letter"},
    )
    assert resp.status_code == 415


def test_upload_rejects_oversized(client):
    # 11 MB file
    big = b"x" * (11 * 1024 * 1024)
    resp = client.post(
        "/api/upload",
        files={"file": ("big.txt", io.BytesIO(big), "text/plain")},
        data={"category": "query_letter"},
    )
    assert resp.status_code == 413


def test_upload_truncates_to_2000_words(client):
    words = " ".join([f"word{i}" for i in range(3000)])
    resp = client.post(
        "/api/upload",
        files={"file": ("long.txt", io.BytesIO(words.encode()), "text/plain")},
        data={"category": "query_letter"},
    )
    assert resp.status_code == 200
    assert resp.json()["word_count"] == 2000


def test_upload_returns_word_count(client):
    content = b"one two three four five"
    resp = client.post(
        "/api/upload",
        files={"file": ("count.txt", io.BytesIO(content), "text/plain")},
        data={"category": "synopsis"},
    )
    assert resp.status_code == 200
    assert resp.json()["word_count"] == 5
