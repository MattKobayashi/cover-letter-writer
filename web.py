import os
import io
import requests
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
from pypdf import PdfReader

app = FastAPI()


@app.get("/health", response_class=PlainTextResponse, include_in_schema=False)
def health_check() -> str:
    """Simple health-check endpoint used by load-balancers / orchestration."""
    return "ok"


def generate_coverletter(api_key, model, prompt):
    """Generates cover letter content using OpenRouter API.

    Args:
        api_key (str): OpenRouter API key (optional if env var set)
        model (str): Model name from OpenRouter's model catalog
        prompt (str): Complete prompt for LLM to generate cover letter

    Returns:
        str: Generated cover letter content from successful API response

    Raises:
        Exception: For API errors, missing key, or unexpected response format
    """
    headers = {
        'Authorization': f'Bearer {api_key or os.getenv("OPENROUTER_API_KEY")}',
        'Content-Type': 'application/json'
    }

    if not headers['Authorization'].split()[-1]:
        raise ValueError("Missing API key")

    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}]
            },
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}") from e

    try:
        result = response.json()
        return result['choices'][0]['message']['content']
    except (KeyError, IndexError) as e:
        raise Exception("Unexpected API response format") from e
    except Exception as e:
        raise Exception(f"Error processing response: {str(e)}") from e


def extract_pdf_text_bytes(file_bytes: bytes) -> str:
    """Extract text content from PDF bytes.

    Converts the provided bytes into a PDF document using an in-memory buffer,
    then extracts and concatenates the text content from all pages.

    Parameters:
        file_bytes (bytes): The raw bytes of a PDF file

    Returns:
        str: The extracted text from all pages of the PDF, joined with newlines
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    # Concatenate the text from all PDF pages.
    return "\n".join(page.extract_text() for page in reader.pages)


@app.get("/", response_class=HTMLResponse)
def read_form():
    """Render the cover letter generation form.

    Returns an HTML page containing a form where users can upload their resume
    and job description PDFs, specify language preferences, and provide an API key
    for generating a customized cover letter.

    Returns:
        HTMLResponse: A webpage with the cover letter generation form
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Generate Cover Letter</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <script>
        function disableSubmit() {
            var btn = document.getElementById("submitBtn");
            btn.disabled = true;
            btn.innerText = "Loading...";
        }
        </script>
    </head>
    <body>
    <div class="container mt-5">
        <h1>Generate Cover Letter</h1>
        <p />
        <form action="/generate" method="post" enctype="multipart/form-data" onsubmit="disableSubmit()">
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
                <input type="text" class="form-control" id="model" name="model" value="google/gemini-2.0-flash-001">
            </div>
            <div class="mb-3">
                <label for="lang" class="form-label">Language</label>
                <input type="text" class="form-control" id="lang" name="lang" value="English (Australia)">
            </div>
            <div class="mb-3">
                <label for="api_key" class="form-label"><a href="https://openrouter.ai/settings/keys" target="_blank">OpenRouter</a> API Key</label>
                <input type="text" class="form-control" id="api_key" name="api_key" required>
            </div>
            <button type="submit" id="submitBtn" class="btn btn-primary">Generate</button>
        </form>
    </div>
    </body>
    </html>
    """


@app.post("/generate", response_class=HTMLResponse)
async def generate_cover_letter_web(
    resume: UploadFile = File(...),
    job_pdf: UploadFile = File(...),
    model: str = Form("google/gemini-2.0-flash-001"),
    lang: str = Form("English (Australia)"),
    api_key: str = Form(...)
):
    """Generate a cover letter from uploaded resume and job description PDFs.

    Extracts text from the uploaded PDF files, creates a prompt that combines
    the resume text and job description, and calls the AI model to generate
    a customized cover letter. Returns the result as an HTML page with the
    generated cover letter and options to copy it to clipboard.

    Parameters:
        resume (UploadFile): The user's resume in PDF format
        job_pdf (UploadFile): The job description in PDF format
        model (str): The AI model to use for generation
        lang (str): The language to use for the cover letter
        api_key (str): The OpenRouter API key for authentication

    Returns:
        HTMLResponse: A webpage containing the generated cover letter with 
                      copy-to-clipboard functionality
    """
    try:
        # Read file bytes from uploads.
        resume_bytes = await resume.read()
        job_bytes = await job_pdf.read()

        # Extract text using our helper.
        resume_text = extract_pdf_text_bytes(resume_bytes)
        job_text = extract_pdf_text_bytes(job_bytes)

        # Build the prompt (mirroring generate.py's prompt).
        prompt = f"""Write a cover letter for a job application using this resume:
{resume_text}

And this job advertisement:
{job_text}

Focus on matching key skills and experience. Use professional tone. Write in {lang}."""

        # Generate cover letter using our function.
        cover_letter = generate_coverletter(api_key, model, prompt)

        # Return the result within a Bootstrap-styled page.
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Generated Cover Letter</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
        <div class="container mt-5">
            <h1>Generated Cover Letter</h1>
            <p />
            <pre id="coverLetterText" class="bg-light p-3">{cover_letter}</pre>
            <button type="button" class="btn btn-info mt-3" onclick="copyToClipboard()">Copy Cover Letter</button>
            <a href="/" class="btn btn-secondary mt-3">New Cover Letter</a>
            <script>
            function copyToClipboard() {{
                var text = document.getElementById("coverLetterText").innerText;
                navigator.clipboard.writeText(text)
                    .then(() => alert("Cover letter copied to clipboard!"))
                    .catch(err => alert("Error copying text: " + err));
            }}
            </script>
        </div>
        </body>
        </html>
        """
    except Exception:
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Error</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
        <div class="container mt-5">
            <h1>Error</h1>
            <div class="alert alert-danger">An error has occurred!</div>
            <a href="/" class="btn btn-primary">Try Again</a>
        </div>
        </body>
        </html>
        """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web:app", host="0.0.0.0", port=8000, reload=True)
