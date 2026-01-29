# Agent Instructions for cover-letter-writer

This document provides essential guidelines and technical references for AI agents (like yourself) operating within this repository. Adhering to these standards ensures consistency, maintainability, and reliability of the codebase.

---

## 1. Development Environment & Commands

The project utilizes `uv` for ultra-fast Python dependency management and task execution.

### Environment Management
- **Sync Environment**: `uv sync`
  Ensures the local `.venv` matches the `uv.lock` file.
- **Update Dependencies**: `uv lock --upgrade`
  Updates all dependencies to their latest compatible versions.
- **Run Scripts**: `uv run <script.py>`
  Executes a script within the project's virtual environment.

### Testing (Pytest)
Testing is handled by `pytest`. Mocking is frequently used to avoid real API calls.
- **Run All Tests**: `uv run pytest`
- **Run Verbose**: `uv run pytest -v`
- **Run Single File**: `uv run pytest tests/test_web.py`
- **Run Single Test Case**: `uv run pytest tests/test_web.py::test_extract_pdf_text_bytes`
- **CI Test Command**: `uv run --dev python3 -m pytest -v tests/`

### Linting & Formatting
- **Pre-commit**: `uv run pre-commit run --all-files`
  This project uses `pre-commit` to manage hooks like `gitleaks`, `trailing-whitespace`, and `end-of-file-fixer`.
- **Standards**: Follow PEP 8. Use 4 spaces for indentation. Ensure every file ends with a single newline.

---

## 2. Code Style & Conventions

### Python Specifics
- **Version**: Target Python 3.14.2+.
- **Naming**:
    - Functions/Variables: `snake_case` (e.g., `generate_coverletter`).
    - Classes: `PascalCase` (e.g., `DummyPdf`).
    - Constants: `UPPER_SNAKE_CASE`.
- **Type Hinting**: Mandatory for all function signatures. Use the `-> None` for functions that return nothing.
    - *Example*: `def process_data(input_str: str) -> list[int]:`
- **Docstrings**: Use Google-style docstrings. Include `Args`, `Returns`, and `Raises` sections where applicable.
  ```python
  def extract_text(file_bytes: bytes) -> str:
      """Extracts text from PDF bytes.

      Args:
          file_bytes: The raw bytes of the PDF.

      Returns:
          The concatenated text from all pages.
      """
  ```

### Imports
Organize imports alphabetically in three distinct sections:
1.  **Standard Library**: `os`, `io`, `json`, etc.
2.  **Third-Party**: `fastapi`, `requests`, `pypdf`, etc.
3.  **Local Application**: Any internal modules.

### Error Handling
- **External Calls**: Always wrap network requests (e.g., `requests.post`) in `try-except` blocks.
- **Explicit Reraising**: When catching an exception to provide context, use `raise Exception("msg") from e`.
- **Validation**: Check for essential environment variables or API keys early and raise `ValueError` if missing.

---

## 3. Architecture & Frameworks

### FastAPI (Web Layer)
- **Routes**: Use `@app.get` and `@app.post`.
- **Responses**:
    - Use `HTMLResponse` for web pages.
    - Use `PlainTextResponse` for simple status checks (e.g., `/health`).
- **Form Handling**: Use `Form(...)` for string inputs and `File(...)` with `UploadFile` for PDF uploads.
- **Templates**: Currently, HTML is embedded as strings within `web.py`. If the UI grows, consider moving to Jinja2 templates.

### PDF Processing
- Uses `pypdf.PdfReader` for text extraction.
- PDF content is handled as `bytes` and processed in-memory using `io.BytesIO`.

### LLM Integration
- **Provider**: OpenRouter API.
- **Model Default**: `google/gemini-3-flash-preview`.
- **Timeout**: Set a reasonable timeout (e.g., 30s) for API requests to prevent hanging.

---

## 4. Testing Strategy

- **Mocking**: Use `monkeypatch` to replace real network calls (`requests.post`) and file system operations.
- **Dummy Classes**: Create minimal dummy classes to simulate complex objects like `PdfReader` and its pages.
- **Endpoint Tests**: Use `fastapi.testclient.TestClient` to verify HTTP status codes and response content (especially looking for specific HTML elements or text strings).

---

## 5. Deployment (Docker)

- **Dockerfile**: Uses a multi-stage build starting from `python:3.14.2-slim-trixie`.
- **Security**: Copies `uv` binary from the official image to ensure reproducible environments.
- **Healthcheck**: Implemented via `curl` against the `/health` endpoint.
- **Startup**: The container runs `python3 /app/web.py` by default.

---

## 6. AI Rules & Integration

- **Cursor Rules**: No specific `.cursorrules` detected.
- **Copilot Rules**: No specific `.github/copilot-instructions.md` detected.
- **General Instruction**: Always read `web.py` before making changes to the core logic, as it contains both the backend API and the frontend UI logic.

---

## 7. Operational Guidelines for Agents

1.  **Read First**: Before editing, use the `Read` tool on `web.py` and `pyproject.toml`.
2.  **Test Proactively**: After any logic change, run `uv run pytest`.
3.  **Verify UI**: If changing HTML strings in `web.py`, ensure the Bootstrap classes remain consistent (v5.3.7 is currently used).
4.  **Security**: NEVER commit or hardcode API keys. Always use environment variables or form inputs.
5.  **Documentation**: If you add a new endpoint or major helper function, update the docstrings and this `AGENTS.md` if necessary.

---
*Created on 2026-01-29. This file is intended to be maintained by both humans and AI agents.*
