# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pypdf2==3.0.1",
#     "requests==2.32.3",
# ]
# ///

import argparse
import os
import sys
from PyPDF2 import PdfReader
import requests

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Generate a cover letter with the help of a LLM'
    )
    parser.add_argument(
        'resume',
        help='Path to resume in PDF format'
    )
    parser.add_argument(
        'job_pdf',
        help='Path to job advertisement in PDF format'
    )
    parser.add_argument(
        '--model',
        default='mistralai/mistral-large-2411',
        help='OpenRouter model name'
    )
    parser.add_argument(
        '--lang',
        default='Australian English',
        help='Language for cover letter'
    )
    parser.add_argument(
        '--api-key',
        help='OpenRouter API key (or use OPENROUTER_API_KEY env var)'
    )
    args = parser.parse_args()

    # Validate input files exist
    for f in [args.resume, args.job_pdf]:
        if not os.path.exists(f):
            sys.exit(f"Input file not found: {f}")

    try:
        print("Extracting text from PDF files...")
        resume_text = extract_pdf_text(args.resume)
        job_text = extract_pdf_text(args.job_pdf)

        prompt = f"""Write a {args.lang} cover letter using this resume:
{resume_text}

And this job advertisement:
{job_text}

Focus on matching key skills and experience. Use professional tone."""

        print(
            f"\nGenerating cover letter in {args.lang} using model {args.model}"
        )
        print(generate_coverletter(args.api_key, args.model, prompt))
    except Exception as e:
        sys.exit(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()


# Add PDF text extraction function
def extract_pdf_text(file_path):
    """Extracts text content from a PDF file.

    Args:
        file_path (str): Path to PDF file to extract text from

    Returns:
        str: Concatenated text from all PDF pages as a single string

    Raises:
        SystemExit: If file is not found, inaccessible, or unreadable
    """
    try:
        with open(file_path, 'rb') as f:
            pdf = PdfReader(f)
            return "\n".join([page.extract_text() for page in pdf.pages])
    except FileNotFoundError:
        sys.exit(f"Error: File {file_path} not found")
    except PermissionError:
        sys.exit(f"Error: No permission to read {file_path}")
    except Exception as e:
        sys.exit(f"Error reading {file_path}: {str(e)}")


# Add API request function
def generate_coverletter(api_key, model, prompt):
    """Generates cover letter content using OpenRouter API.

    Args:
        api_key (str): OpenRouter API key (optional if env var set)
        model (str): Model name from OpenRouter's model catalog
        prompt (str): Complete prompt for LLM to generate cover letter

    Returns:
        str: Generated cover letter content from successful API response

    Raises:
        SystemExit: For API errors, missing key, or unexpected response format
    """
    headers = {
        'Authorization': f'Bearer {api_key or os.getenv("OPENROUTER_API_KEY")}',
        'Content-Type': 'application/json'
    }

    if not headers['Authorization'].split()[-1]:
        sys.exit(
            "Error: Missing API key. Use --api-key or set OPENROUTER_API_KEY"
        )

    try:
        print("Waiting for LLM response...")
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
        sys.exit(f"API request failed: {str(e)}")

    try:
        result = response.json()
        print("LLM response received.\n")
        return result['choices'][0]['message']['content']
    except KeyError:
        sys.exit("Unexpected API response format")
    except Exception as e:
        sys.exit(f"Error processing response: {str(e)}")


