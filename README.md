# cover-letter-writer

## Setup

1. Get an API key from your [OpenRouter](https://openrouter.ai/settings/keys) account.
2. Install [Poetry](https://python-poetry.org/docs/#installation). On macOS, installing via [Homebrew](https://formulae.brew.sh/formula/poetry#default) is easiest.
3. Install the project:

   ```shell
   poetry install
   ```

4. Run the script with your preferred options.

4. Run the script with your preferred options.

## Usage

```shell
usage: generate_cover_letter.py [-h] [--model MODEL] [--lang LANG] [--api-key API_KEY] resume job_pdf

Generate cover letter using LLM

positional arguments:
  resume             Path to resume PDF file
  job_pdf            Path to job advertisement PDF

options:
  -h, --help         show this help message and exit
  --model MODEL      OpenRouter model name
  --lang LANG        Language for cover letter
  --api-key API_KEY  OpenRouter API key (or use OPENROUTER_API_KEY env var)
```
