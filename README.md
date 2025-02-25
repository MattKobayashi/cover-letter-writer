# cover-letter-writer

## Setup

1. Get an API key from your [OpenRouter](https://openrouter.ai/settings/keys) account.
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/#homebrew).
3. Run the script with your preferred options:

```shell
uv run generate.py <resume PDF> <job PDF> --api-key <API key>
```

## Usage

```shell
usage: generate.py [-h] [--model MODEL] [--lang LANG] [--api-key API_KEY] resume job_pdf

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
