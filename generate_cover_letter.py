import argparse
import os
from PyPDF2 import PdfReader
import requests

# Add argument parsing
parser = argparse.ArgumentParser(description='Generate cover letter using LLM')
parser.add_argument('resume', help='Path to resume PDF file')
parser.add_argument('job_pdf', help='Path to job advertisement PDF')
parser.add_argument('--model', default='mistralai/mistral-large-2411', help='OpenRouter model name')
parser.add_argument('--lang', default='Australian English', help='Language for cover letter')
parser.add_argument('--api-key', help='OpenRouter API key (or use OPENROUTER_API_KEY env var)')
args = parser.parse_args()


# Add PDF text extraction function
def extract_pdf_text(file_path):
    with open(file_path, 'rb') as f:
        pdf = PdfReader(f)
        return "\n".join([page.extract_text() for page in pdf.pages])


# Add API request function
def generate_coverletter(api_key, model, prompt):
    headers = {
        'Authorization': f'Bearer {api_key or os.getenv("OPENROUTER_API_KEY")}',
        'Content-Type': 'application/json'
    }
    response = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        json={
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}]
        },
        headers=headers
    )
    return response.json()['choices'][0]['message']['content']


# Main execution
if __name__ == "__main__":
    resume_text = extract_pdf_text(args.resume)
    job_text = extract_pdf_text(args.job_pdf)

    prompt = f"""Write a {args.lang} cover letter using this resume:
{resume_text}

And this job advertisement:
{job_text}

Focus on matching key skills and experience. Use professional tone."""

    print(generate_coverletter(args.api_key, args.model, prompt))
