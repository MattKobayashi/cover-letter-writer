import io
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pypdf import PdfReader
from generate import generate_coverletter  # reuse your API call function

app = FastAPI()


def extract_pdf_text_bytes(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    # Concatenate the text from all PDF pages.
    return "\n".join(page.extract_text() for page in reader.pages)


@app.get("/", response_class=HTMLResponse)
def read_form():
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
                <input type="text" class="form-control" id="model" name="model" value="mistralai/mistral-large-2411">
            </div>
            <div class="mb-3">
                <label for="lang" class="form-label">Language</label>
                <input type="text" class="form-control" id="lang" name="lang" value="Australian English">
            </div>
            <div class="mb-3">
                <label for="api_key" class="form-label"><a href="https://openrouter.ai/settings/keys" target="_blank">OpenRouter</a> API Key</label>
                <input type="text" class="form-control" id="api_key" name="api_key" placeholder="Leave blank to use environment variable">
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
    model: str = Form("mistralai/mistral-large-2411"),
    lang: str = Form("Australian English"),
    api_key: str = Form(None)
):
    # Read file bytes from uploads.
    resume_bytes = await resume.read()
    job_bytes = await job_pdf.read()

    # Extract text using our helper.
    resume_text = extract_pdf_text_bytes(resume_bytes)
    job_text = extract_pdf_text_bytes(job_bytes)

    # Build the prompt (mirroring generate.py's prompt).
    prompt = f"""Write a {lang} cover letter using this resume:
{resume_text}

And this job advertisement:
{job_text}

Focus on matching key skills and experience. Use professional tone."""

    # Generate cover letter by reusing your existing function.
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
        <pre class="bg-light p-3">{cover_letter}</pre>
        <a href="/" class="btn btn-secondary mt-3">Generate Another</a>
    </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web:app", host="0.0.0.0", port=8000, reload=True)
