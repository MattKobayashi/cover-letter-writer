import pytest
import requests
from fastapi.testclient import TestClient

import web
from web import (
    CSRF_COOKIE_NAME,
    OpenRouterError,
    app,
    extract_pdf_text,
    extract_pdf_text_bytes,
    generate_coverletter,
    get_openrouter_error_response,
)

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


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    """Reset per-client state so tests do not interfere with each other."""
    web._rate_limit_store.clear()
    client.cookies.clear()
    yield
    web._rate_limit_store.clear()
    client.cookies.clear()


def with_csrf(data: dict) -> dict:
    """Fetch the form to obtain a CSRF cookie and return data with a matching token."""
    client.get("/")
    token = client.cookies.get(CSRF_COOKIE_NAME)
    return {**data, "csrf_token": token}


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


def test_extract_pdf_text_rejects_empty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf(None))
    with pytest.raises(ValueError, match="does not contain extractable text"):
        extract_pdf_text(PDF_BYTES, "Resume")


def test_extract_pdf_text_handles_unreadable_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_error(stream):
        raise RuntimeError("broken pdf")

    monkeypatch.setattr("web.PdfReader", raise_error)
    with pytest.raises(ValueError, match="could not be read as a PDF"):
        extract_pdf_text(PDF_BYTES, "Resume")


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.text == "ok"


def test_security_headers_present() -> None:
    response = client.get("/")
    assert "Content-Security-Policy" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


@pytest.mark.parametrize(
    ("status_code", "expected_status", "expected_fragment"),
    [
        (401, 400, "rejected the API key"),
        (403, 400, "rejected the API key"),
        (402, 400, "insufficient credits"),
        (404, 400, "model was not found"),
        (413, 400, "prompt was too large"),
        (429, 429, "rate limited"),
        (418, 400, "OpenRouter rejected the request."),
        (500, 502, "Failed to generate the cover letter."),
        (None, 502, "Failed to generate the cover letter."),
    ],
)
def test_get_openrouter_error_response(
    status_code: int | None, expected_status: int, expected_fragment: str
) -> None:
    message, mapped_status = get_openrouter_error_response(
        OpenRouterError("boom", status_code=status_code)
    )
    assert mapped_status == expected_status
    assert expected_fragment in message


def test_get_form() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "<form" in response.text
    assert 'id="submitBtn"' in response.text
    assert 'type="password"' in response.text
    assert 'name="csrf_token"' in response.text
    assert response.cookies.get(CSRF_COOKIE_NAME) is not None


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


def test_generate_coverletter_preserves_http_status_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_post(*args, **kwargs):
        class MockResponse:
            def raise_for_status(self) -> None:
                error = requests.exceptions.HTTPError("unauthorized")
                error.response = type("Response", (), {"status_code": 401})()
                raise error

        return MockResponse()

    monkeypatch.setattr("requests.post", mock_post)

    with pytest.raises(OpenRouterError) as excinfo:
        generate_coverletter("dummy-key", "dummy-model", "dummy-prompt")

    assert excinfo.value.status_code == 401


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
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )
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
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 200
    assert "&lt;img src=x onerror=window.__attack=true&gt;" in response.text
    assert malicious_text not in response.text


def test_generate_endpoint_rejects_missing_csrf_token() -> None:
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

    assert response.status_code == 403
    assert "could not be verified" in response.text


def test_generate_endpoint_rejects_mismatched_csrf_token() -> None:
    client.get("/")
    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = {
        "model": "dummy-model",
        "lang": "dummy-lang",
        "api_key": "dummy-api-key",
        "csrf_token": "not-the-cookie-value",
    }
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 403
    assert "could not be verified" in response.text


def test_generate_endpoint_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web, "RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(
        "web.generate_coverletter",
        lambda api_key, model, prompt: "Fake Cover Letter",
    )
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())

    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )

    first = client.post("/generate", files=files, data=data)
    assert first.status_code == 200

    second = client.post("/generate", files=files, data=data)
    assert second.status_code == 429
    assert "Too many requests." in second.text


def test_generate_endpoint_rejects_blank_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())

    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "   ",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert "Missing API key." in response.text


def test_generate_endpoint_rejects_missing_api_key_field() -> None:
    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert "Missing API key." in response.text


def test_generate_endpoint_rejects_missing_job_pdf_field() -> None:
    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert "Missing job advertisement PDF." in response.text


def test_generate_endpoint_rejects_non_pdf_upload() -> None:
    files = {
        "resume": ("resume.txt", b"not a pdf", "text/plain"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert (
        "The submitted files were invalid. Upload extractable PDF files up to 5 MB and try again."
        in response.text
    )


def test_generate_endpoint_rejects_upload_without_pdf_content_type() -> None:
    files = {
        "resume": ("resume.pdf", PDF_BYTES),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert (
        "The submitted files were invalid. Upload extractable PDF files up to 5 MB and try again."
        in response.text
    )


def test_generate_endpoint_rejects_invalid_pdf_header() -> None:
    files = {
        "resume": ("resume.pdf", b"this file lacks a pdf header", "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert (
        "The submitted files were invalid. Upload extractable PDF files up to 5 MB and try again."
        in response.text
    )


def test_generate_endpoint_rejects_oversized_upload() -> None:
    oversized = PDF_BYTES + b"0" * (5 * 1024 * 1024 + 1)
    files = {
        "resume": ("resume.pdf", oversized, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert (
        "The submitted files were invalid. Upload extractable PDF files up to 5 MB and try again."
        in response.text
    )


def test_generate_endpoint_hides_validation_exception_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "web.extract_pdf_text",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("secret path: /srv/app/private.pdf")
        ),
    )

    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert (
        "The submitted files were invalid. Upload extractable PDF files up to 5 MB and try again."
        in response.text
    )
    assert "secret path: /srv/app/private.pdf" not in response.text


def test_generate_endpoint_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_generate_error(*args, **kwargs):
        raise OpenRouterError("OpenRouter request failed.", status_code=500)

    monkeypatch.setattr("web.generate_coverletter", mock_generate_error)
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())

    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 502
    assert "Failed to generate the cover letter. Please try again." in response.text
    assert "Try Again" in response.text


def test_generate_endpoint_shows_invalid_api_key_error_from_openrouter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_generate_error(*args, **kwargs):
        raise OpenRouterError("OpenRouter request failed.", status_code=401)

    monkeypatch.setattr("web.generate_coverletter", mock_generate_error)
    monkeypatch.setattr("web.PdfReader", lambda stream: DummyPdf())

    files = {
        "resume": ("resume.pdf", PDF_BYTES, "application/pdf"),
        "job_pdf": ("job_pdf.pdf", PDF_BYTES, "application/pdf"),
    }
    data = with_csrf(
        {
            "model": "dummy-model",
            "lang": "dummy-lang",
            "api_key": "dummy-api-key",
        }
    )
    response = client.post("/generate", files=files, data=data)

    assert response.status_code == 400
    assert (
        "OpenRouter rejected the API key. Check your API key and try again."
        in response.text
    )
