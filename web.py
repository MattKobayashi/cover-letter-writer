#!/usr/bin/env python3
import asyncio
import html
import io
import logging

import requests
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from pypdf import PdfReader
from starlette.concurrency import run_in_threadpool

BOOTSTRAP_STYLESHEET_URL = (
    "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.7/css/bootstrap.min.css"
)
BOOTSTRAP_STYLESHEET_INTEGRITY = (
    "sha512-fw7f+TcMjTb7bpbLJZlP8g2Y4XcCyFZW8uy8HsRZsH/SwbMw0plKHFHr99DN3l04"
    "VsYNwvzicUX/6qurvIxbxw=="
)
DEFAULT_MODEL = "openai/gpt-5.4-nano"
DEFAULT_LANGUAGE = "English (Australia)"
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
MAX_PROMPT_SOURCE_CHARS = 20_000
PDF_HEADER = b"%PDF-"

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/health", response_class=PlainTextResponse, include_in_schema=False)
def health_check() -> str:
    """Simple health-check endpoint used by load-balancers / orchestration."""
    return "ok"


def render_page(title: str, body: str, *, status_code: int = 200) -> HTMLResponse:
    """Render a Bootstrap-backed HTML page.

    Args:
        title: Page title shown in the browser and heading.
        body: Trusted HTML body content for the page.
        status_code: HTTP status code to return.

    Returns:
        A rendered HTML response.
    """
    safe_title = html.escape(title)
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{safe_title}</title>
            <link href="{BOOTSTRAP_STYLESHEET_URL}" rel="stylesheet" integrity="{BOOTSTRAP_STYLESHEET_INTEGRITY}" crossorigin="anonymous">
        </head>
        <body>
        <div class="container mt-5 mb-5">
            {body}
        </div>
        </body>
        </html>
        """,
        status_code=status_code,
    )


def render_error_page(message: str, *, status_code: int) -> HTMLResponse:
    """Render a user-facing error page.

    Args:
        message: Error message to show to the user.
        status_code: HTTP status code to return.

    Returns:
        A rendered HTML response.
    """
    safe_message = html.escape(message)
    return render_page(
        "Error",
        f"""
        <h1>Error</h1>
        <div class="alert alert-danger" role="alert">{safe_message}</div>
        <a href="/" class="btn btn-primary">Try Again</a>
        """,
        status_code=status_code,
    )


def generate_coverletter(api_key: str, model: str, prompt: str) -> str:
    """Generate cover letter content using the OpenRouter API.

    Args:
        api_key: OpenRouter API key.
        model: Model name from OpenRouter's model catalog.
        prompt: Complete prompt for the LLM.

    Returns:
        Generated cover letter content.

    Raises:
        ValueError: If a required input is missing.
        RuntimeError: If the API call fails or returns an unexpected response.
    """
    api_key = api_key.strip()
    model = model.strip()
    prompt = prompt.strip()

    if not api_key:
        raise ValueError("Missing API key.")
    if not model:
        raise ValueError("Missing model name.")
    if not prompt:
        raise ValueError("Missing prompt.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        status_code = (
            exc.response.status_code if exc.response is not None else "unknown"
        )
        raise RuntimeError(
            f"OpenRouter request failed with status code {status_code}."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError("Could not reach OpenRouter.") from exc

    try:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError("OpenRouter returned an unexpected response.") from exc

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("OpenRouter returned an empty response.")

    return content.strip()


def extract_pdf_text_bytes(file_bytes: bytes) -> str:
    """Extract text content from PDF bytes.

    Args:
        file_bytes: Raw bytes of a PDF file.

    Returns:
        Extracted text from all pages joined with newlines.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_pdf_text(file_bytes: bytes, label: str) -> str:
    """Extract and validate user-supplied PDF text.

    Args:
        file_bytes: Raw PDF bytes.
        label: Friendly label for user-facing errors.

    Returns:
        Extracted text trimmed to a reasonable prompt size.

    Raises:
        ValueError: If the file cannot be parsed or contains no extractable text.
    """
    try:
        extracted_text = extract_pdf_text_bytes(file_bytes)
    except Exception as exc:
        raise ValueError(f"{label} could not be read as a PDF.") from exc

    normalized_text = extracted_text.strip()
    if not normalized_text:
        raise ValueError(f"{label} does not contain extractable text.")

    return normalized_text[:MAX_PROMPT_SOURCE_CHARS]


async def read_uploaded_pdf(upload: UploadFile, label: str) -> bytes:
    """Read, size-check, and validate an uploaded PDF.

    Args:
        upload: Uploaded file from the request.
        label: Friendly label for user-facing errors.

    Returns:
        Raw file bytes.

    Raises:
        ValueError: If the upload is too large or not a PDF.
    """
    if upload.content_type and upload.content_type != "application/pdf":
        raise ValueError(f"{label} must be uploaded as a PDF.")

    file_bytes = await upload.read(MAX_UPLOAD_SIZE_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(f"{label} must be 5 MB or smaller.")

    if PDF_HEADER not in file_bytes[:1024]:
        raise ValueError(f"{label} must be a valid PDF file.")

    return file_bytes


@app.get("/", response_class=HTMLResponse)
def read_form() -> HTMLResponse:
    """Render the cover letter generation form.

    Returns:
        A webpage with the cover letter generation form.
    """
    return render_page(
        "Generate Cover Letter",
        f"""
        <h1>Generate Cover Letter</h1>
        <form action="/generate" method="post" enctype="multipart/form-data" id="coverLetterForm">
            <div class="mb-3">
                <label for="resume" class="form-label">Resume (PDF)</label>
                <input type="file" class="form-control" id="resume" name="resume" accept="application/pdf" required>
            </div>
            <div class="mb-3">
                <label for="job_pdf" class="form-label">Job Advertisement (PDF)</label>
                <input type="file" class="form-control" id="job_pdf" name="job_pdf" accept="application/pdf" required>
            </div>
            <div class="mb-3">
                <label for="model" class="form-label">Model</label>
                <input type="text" class="form-control" id="model" name="model" value="{html.escape(DEFAULT_MODEL, quote=True)}">
            </div>
            <div class="mb-3">
                <label for="lang" class="form-label">Language</label>
                <input type="text" class="form-control" id="lang" name="lang" value="{html.escape(DEFAULT_LANGUAGE, quote=True)}">
            </div>
            <div class="mb-3">
                <label for="api_key" class="form-label"><a href="https://openrouter.ai/settings/keys" target="_blank" rel="noopener noreferrer">OpenRouter</a> API Key</label>
                <input type="password" class="form-control" id="api_key" name="api_key" autocomplete="off" autocapitalize="off" spellcheck="false" required>
            </div>
            <button type="submit" id="submitBtn" class="btn btn-primary">Generate</button>
        </form>
        <script>
        document.getElementById("coverLetterForm").addEventListener("submit", function () {{
            var btn = document.getElementById("submitBtn");
            btn.disabled = true;
            btn.innerText = "Loading...";
        }});
        </script>
        """,
    )


@app.post("/generate", response_class=HTMLResponse)
async def generate_cover_letter_web(
    resume: UploadFile = File(...),
    job_pdf: UploadFile = File(...),
    model: str = Form(DEFAULT_MODEL),
    lang: str = Form(DEFAULT_LANGUAGE),
    api_key: str = Form(...),
) -> HTMLResponse:
    """Generate a cover letter from uploaded resume and job description PDFs.

    Args:
        resume: The user's resume in PDF format.
        job_pdf: The job description in PDF format.
        model: The AI model to use for generation.
        lang: The language to use for the cover letter.
        api_key: The OpenRouter API key for authentication.

    Returns:
        A webpage containing the generated cover letter.
    """
    try:
        model_name = model.strip() or DEFAULT_MODEL
        language = lang.strip() or DEFAULT_LANGUAGE

        resume_bytes, job_bytes = await asyncio.gather(
            read_uploaded_pdf(resume, "Resume"),
            read_uploaded_pdf(job_pdf, "Job advertisement"),
        )

        resume_text, job_text = await asyncio.gather(
            run_in_threadpool(extract_pdf_text, resume_bytes, "Resume"),
            run_in_threadpool(extract_pdf_text, job_bytes, "Job advertisement"),
        )

        prompt = f"""Write a cover letter for a job application using this resume:
{resume_text}

And this job advertisement:
{job_text}

Focus on matching key skills and experience. Use professional tone. Write in {language}."""

        cover_letter = await run_in_threadpool(
            generate_coverletter,
            api_key,
            model_name,
            prompt,
        )
        escaped_cover_letter = html.escape(cover_letter)

        return render_page(
            "Generated Cover Letter",
            f"""
            <h1>Generated Cover Letter</h1>
            <pre id="coverLetterText" class="bg-light p-3">{escaped_cover_letter}</pre>
            <button type="button" id="copyBtn" class="btn btn-info mt-3">Copy Cover Letter</button>
            <a href="/" class="btn btn-secondary mt-3">New Cover Letter</a>
            <script>
            document.getElementById("copyBtn").addEventListener("click", async function () {{
                var text = document.getElementById("coverLetterText").innerText;
                try {{
                    await navigator.clipboard.writeText(text);
                    alert("Cover letter copied to clipboard!");
                }} catch (err) {{
                    alert("Error copying text: " + err);
                }}
            }});
            </script>
            """,
        )
    except ValueError as exc:
        logger.info("Invalid cover letter request: %s", exc)
        return render_error_page(str(exc), status_code=400)
    except RuntimeError:
        logger.exception("Cover letter generation failed")
        return render_error_page(
            "Failed to generate the cover letter. Please try again.",
            status_code=502,
        )
    except Exception:
        logger.exception("Unexpected error while generating cover letter")
        return render_error_page(
            "An unexpected error occurred. Please try again.",
            status_code=500,
        )
    finally:
        await resume.close()
        await job_pdf.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web:app", host="0.0.0.0", port=8000, reload=False)
