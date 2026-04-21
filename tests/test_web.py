import pytest
from fastapi.testclient import TestClient

from web import app, extract_pdf_text_bytes, generate_coverletter

client = TestClient(app)
PDF_BYTES = b"%PDF-1.7 dummy pdf"


class DummyPage:
    def __init__(self, content: str | None = "Page content") -> None:
        self.content = content

    def extract_text(self) -> str | None:
        return self.content


class DummyPdf:
    def __init__(self, *contents: str | None) -> None:
        page_contents = contents or ("Page content", "Page content")
        self.pages = [DummyPage(content) for content in page_contents]


def test_extract_pdf_text_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())
    result = extract_pdf_text_bytes(PDF_BYTES)
    assert result == "Page content\nPage content"


def test_extract_pdf_text_bytes_handles_pages_without_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf(None))
    result = extract_pdf_text_bytes(PDF_BYTES)
    assert result == ""


def test_get_form() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "<form" in response.text
    assert 'id="submitBtn"' in response.text
    assert 'type="password"' in response.text


def test_generate_coverletter(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_post(*args, **kwargs):
        class MockResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, list[dict[str, dict[str, str]]]]:
                return {"choices": [{"message": {"content": "Test Cover Letter"}}]}

        return MockResponse()

    monkeypatch.setattr("requests.post", mock_post)

    result = generate_coverletter("dummy-key", "dummy-model", "dummy-prompt")
    assert result == "Test Cover Letter"


def test_generate_coverletter_requires_api_key() -> None:
    with pytest.raises(ValueError, match="Missing API key"):
        generate_coverletter("   ", "dummy-model", "dummy-prompt")


def test_generate_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "web.generate_coverletter",
        lambda api_key, model, prompt: "Fake Cover Letter",
    )
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())

    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = {
        "model": "dummy-model",
        "lang": "dummy-lang",
        "api_key": "dummy-api-key",
    }
    response = client.post("/generate", files=files, data=data)
    assert response.status_code == 200
    assert "Fake Cover Letter" in response.text


def test_generate_endpoint_escapes_cover_letter_html(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    malicious_text = "<img src=x onerror=window.__attack=true>"
    monkeypatch.setattr(
        "web.generate_coverletter",
        lambda api_key, model, prompt: malicious_text,
    )
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())

    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = {
        "model": "dummy-model",
        "lang": "dummy-lang",
        "api_key": "dummy-api-key",
    }
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 200
    assert "&lt;img src=x onerror=window.__attack=true&gt;" in response.text
    assert malicious_text not in response.text


def test_generate_endpoint_rejects_blank_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())

    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = {
        "model": "dummy-model",
        "lang": "dummy-lang",
        "api_key": "   ",
    }
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert "Missing API key." in response.text


def test_generate_endpoint_rejects_non_pdf_upload() -> None:
    files = {
        "resume": ("resume.txt", b"not a pdf", "text/plain"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = {
        "model": "dummy-model",
        "lang": "dummy-lang",
        "api_key": "dummy-api-key",
    }
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert "Resume must be uploaded as a PDF." in response.text


def test_generate_endpoint_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_generate_error(*args, **kwargs):
        raise RuntimeError("OpenRouter request failed.")

    monkeypatch.setattr("web.generate_coverletter", mock_generate_error)
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())

    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = {
        "model": "dummy-model",
        "lang": "dummy-lang",
        "api_key": "dummy-api-key",
    }
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 502
    assert "Failed to generate the cover letter. Please try again." in response.text
    assert "Try Again" in response.text
