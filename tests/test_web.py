import io
import pytest
from fastapi.testclient import TestClient
from web import app, extract_pdf_text_bytes

client = TestClient(app)


# Dummy classes for PdfReader replacement in web.py.
class DummyPage:
    def extract_text(self):
        return "Page content"


class DummyPdf:
    pages = [DummyPage(), DummyPage()]


def test_extract_pdf_text_bytes(monkeypatch):
    # Replace PdfReader in web.py to return dummy pages.
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())
    result = extract_pdf_text_bytes(b"dummy bytes")
    assert result == "Page content\nPage content"


def test_get_form():
    response = client.get("/")
    assert response.status_code == 200
    # Check that we see the HTML form and the submit button (with id="submitBtn").
    assert "<form" in response.text
    assert 'id="submitBtn"' in response.text


def test_generate_endpoint(monkeypatch):
    # To avoid a real API call, replace generate_coverletter in web.py with a dummy.
    monkeypatch.setattr("web.generate_coverletter", lambda api_key, model, prompt: "Fake Cover Letter")
    # Also replace PdfReader in extract_pdf_text_bytes.
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())

    files = {
        "resume": ("resume.pdf", b"dummy resume", "application/pdf"),
        "job_pdf": ("job_pdf.pdf", b"dummy job", "application/pdf"),
    }
    data = {
        "model": "dummy-model",
        "lang": "dummy-lang",
        "api_key": "dummy-api-key"
    }
    response = client.post("/generate", files=files, data=data)
    assert response.status_code == 200
    # Check that the returned page includes our dummy cover letter.
    assert "Fake Cover Letter" in response.text
