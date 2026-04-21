# Agent Instructions

## Package Manager

- Use `uv`.
- Sync deps: `uv sync`
- Run the app: `uv run python3 web.py`
- Run all tests: `uv run pytest`
- Run hooks: `uv run pre-commit run --all-files`

## File-Scoped Commands

| Task                | Command                                                                        |
| ------------------- | ------------------------------------------------------------------------------ |
| Test file           | `uv run pytest tests/test_web.py`                                              |
| Test case           | `uv run pytest tests/test_web.py::test_generate_endpoint`                      |
| CI-equivalent tests | `uv run --dev python3 -m pytest -v tests/`                                     |
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

## Testing Notes

- Tests avoid real network and PDF parsing by monkeypatching `web.generate_coverletter` and `web.PdfReader`.
- Container checks rely on `tests/docker-compose.yaml`, container name `cover-letter-writer`, and `/health` returning `ok`.
- Pre-commit only enforces `gitleaks`, `end-of-file-fixer`, and `trailing-whitespace`.

## Commit Attribution

If you create a commit, include:

```
Co-Authored-By: OpenCode <noreply@example.com>
```
