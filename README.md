# cover-letter-writer

## Setup

1. Get an API key from your [OpenRouter](https://openrouter.ai/settings/keys) account.
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/#homebrew).
3. Start the web app:

```shell
uv run python3 web.py
```

4. Open `http://127.0.0.1:8000` in your browser.

## Usage

1. Upload your resume PDF.
2. Upload the job advertisement PDF.
3. Choose the OpenRouter model and output language.
4. Paste your OpenRouter API key.
5. Submit the form to generate a cover letter.

Each request uses the API key supplied in the form. Uploaded files must be sent as `application/pdf`, include a valid `%PDF-` header, contain extractable text, and be 5 MB or smaller.
