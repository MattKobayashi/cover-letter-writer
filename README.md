# cover-letter-writer

## How to use

1. Get an API key from your [OpenRouter](https://openrouter.ai/settings/keys) account.
2. Install [Poetry](https://python-poetry.org/docs/#installation). On macOS, installing via [Homebrew](https://formulae.brew.sh/formula/poetry#default) is easiest.
3. Install the project:

   ```shell
   poetry install
   ```

4. Run the script with your preferred options.

   Minimal usage:

   ```shell
   poetry run python3 generate_cover_letter.py files/resume.pdf files/job.pdf --api-key <your API key here>
   ```
