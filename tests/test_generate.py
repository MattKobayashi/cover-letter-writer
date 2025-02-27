import os
import sys
import tempfile
import pytest
from generate import extract_pdf_text, generate_coverletter


# Dummy classes for PdfReader replacement.
class DummyPage:
    def extract_text(self):
        return "Dummy Page Text"


class DummyPdf:
    pages = [DummyPage(), DummyPage()]


# Dummy replacement for requests.post (success case)
def dummy_requests_post_success(url, json, headers, timeout):
    class DummyResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": "Test cover letter"}}]}
    return DummyResponse()


# Dummy replacement for requests.post (error case)
def dummy_requests_post_error(url, json, headers, timeout):
    from requests.exceptions import RequestException
    raise RequestException("dummy error")


def test_extract_pdf_text_success(monkeypatch):
    # Replace PdfReader in generate.py so it returns dummy pages.
    monkeypatch.setattr("generate.PdfReader", lambda f: DummyPdf())
    # Create a temporary file (its contents are irrelevant due to our monkeypatch).
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"dummy content")
        tmp_filename = tmp.name
    try:
        text = extract_pdf_text(tmp_filename)
        # Expect two pages joined by a newline.
        assert text == "Dummy Page Text\nDummy Page Text"
    finally:
        os.unlink(tmp_filename)


def test_extract_pdf_text_file_not_found():
    # extract_pdf_text calls sys.exit if file not found.
    with pytest.raises(SystemExit):
        extract_pdf_text("non_existent_file.pdf")


def test_generate_coverletter_success(monkeypatch):
    # Replace requests.post in generate.py with our dummy success function.
    monkeypatch.setattr("generate.requests.post", dummy_requests_post_success)
    api_key = "dummy-api-key"
    model = "dummy-model"
    prompt = "dummy prompt"
    result = generate_coverletter(api_key, model, prompt)
    assert result == "Test cover letter"


def test_generate_coverletter_missing_api_key(monkeypatch):
    # Ensure that if no API key is provided (nor in env) the function exits.
    if "OPENROUTER_API_KEY" in os.environ:
        del os.environ["OPENROUTER_API_KEY"]
    with pytest.raises(SystemExit):
        generate_coverletter("", "dummy-model", "dummy prompt")


def test_generate_coverletter_api_error(monkeypatch):
    # Simulate an API request failure.
    monkeypatch.setattr("generate.requests.post", dummy_requests_post_error)
    with pytest.raises(SystemExit):
        generate_coverletter("dummy-api-key", "dummy-model", "dummy prompt")
