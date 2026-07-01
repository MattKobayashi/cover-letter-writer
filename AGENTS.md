# Agent Instructions

## Package Manager

- Use `uv`.
- Sync deps: `uv sync --dev`
- Run the app: `uv run python3 web.py`
- Run all tests: `uv run pytest`
- Lint: `uv run ruff check web.py tests/`
- Format check: `uv run ruff format --check web.py tests/`
- Type check: `uv run mypy web.py`
- Run hooks: `uv run pre-commit run --all-files`

## File-Scoped Commands

| Task                | Command                                                                        |
| ------------------- | ------------------------------------------------------------------------------ |
| Test file           | `uv run pytest tests/test_web.py`                                              |
| Test case           | `uv run pytest tests/test_web.py::test_generate_endpoint`                      |
| CI-equivalent tests | `uv sync --dev && uv run python3 -m pytest -v tests/`                          |
| Docker build        | `docker build -t "cover-letter-writer:test" .`                                 |
| Docker smoke test   | `docker compose -f tests/docker-compose.yaml up --build --detach --timeout 60` |
| Docker cleanup      | `docker compose -f tests/docker-compose.yaml down --timeout 60`                |
| Health check        | `docker inspect --format='{{.State.Health.Status}}' cover-letter-writer`       |

## Structure

- `web.py` is the only app entrypoint; it contains FastAPI routes, inline HTML rendering, PDF extraction, and the OpenRouter call.
- There is no separate CLI entrypoint.
- CI and Docker use Python `3.14.4`; `pyproject.toml` allows `>=3.14,<3.15`.

## Key Conventions

- Keep blocking work out of the async `/generate` route; follow the existing `run_in_threadpool(...)` pattern unless you convert the full stack to async.
- Reuse `render_page()` / `render_error_page()` and the Bootstrap constants in `web.py` instead of duplicating full HTML documents.
- Web requests must use the API key supplied in the form; do not restore server-side env fallback for `/generate`.
- PDF uploads are validated server-side: `application/pdf`, `%PDF-` header, max `5 MB`, and extractable text required. Update `README.md` and tests if this behavior changes.
- Escape generated cover-letter text before rendering it into HTML.
- `/generate` requires a valid double-submit CSRF token (`csrftoken` cookie set by `GET /` must match the `csrf_token` form field) and is rate limited per client IP (`RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS`).
- Security headers (CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) are applied by middleware; keep the CSP in sync with any new external assets.
- Catch specific exceptions in `/generate`; do not add a broad `RuntimeError` catch (rely on the `OpenRouterError` handler and the final `Exception` fallback).

## Testing Notes

- Tests avoid real network and PDF parsing by monkeypatching `web.generate_coverletter` and `web.PdfReader`.
- `/generate` tests must supply CSRF via the `with_csrf(...)` helper; the autouse `_reset_state` fixture clears the rate-limit store and cookies between tests.
- Container checks rely on `tests/docker-compose.yaml`, container name `cover-letter-writer`, and `/health` returning `ok`.
- Pre-commit enforces `gitleaks`, `end-of-file-fixer`, `trailing-whitespace`, `ruff` (check + format), and `mypy`.

## Commit Attribution

If you create a commit, include:

```text
Co-Authored-By: OpenCode <noreply@example.com>
```
