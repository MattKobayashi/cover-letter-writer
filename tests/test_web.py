from fastapi.testclient import TestClient
from web import app, extract_pdf_text_bytes, generate_coverletter

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


def test_generate_coverletter(monkeypatch):
    # Replace requests.post with a dummy function
    def mock_post(*args, **kwargs):
        class MockResponse:
            def raise_for_status(self):
                pass
            def json(self):
                return {"choices": [{"message": {"content": "Test Cover Letter"}}]}
        return MockResponse()

    monkeypatch.setattr("requests.post", mock_post)

    result = generate_coverletter("dummy-key", "dummy-model", "dummy-prompt")
    assert result == "Test Cover Letter"


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


def test_generate_endpoint_error(monkeypatch):
    # Make generate_coverletter raise an exception
    def mock_generate_error(*args, **kwargs):
        raise Exception("Test error message")

    monkeypatch.setattr("web.generate_coverletter", mock_generate_error)
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
    # Check that the returned page includes our error message
    assert "Test error message" in response.text
    assert "Try Again" in response.text
