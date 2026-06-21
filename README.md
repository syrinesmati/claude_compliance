# Claude Compliance

Small CLI utility for scoring a document against a single SAMA Cyber Security Framework evidence requirement.

## What it does

The script in [compliance_scorer.py](compliance_scorer.py) loads the SAMA CSF hierarchy from [sama-csf-hierarchy-level3.json](sama-csf-hierarchy-level3.json), sends the selected requirement and document text to OpenAI, and returns a JSON assessment with:

- `present`: whether the document satisfies the requirement
- `score_percentage`: a 0-100 score
- `reasoning`: a short explanation

## Requirements

- Python 3.10 or newer
- An `OPENAI_API_KEY` environment variable
- The `openai` Python package

## Setup

Install dependencies:

```bash
pip install openai
```

Set your API key:

```bash
set OPENAI_API_KEY=your_api_key
```

On PowerShell, use:

```powershell
$env:OPENAI_API_KEY="your_api_key"
```

## Usage

Run the scorer with a document path and an evidence code from the hierarchy:

```bash
python compliance_scorer.py "my_doc.md" "SAMA-3.1.1-1-L3-1"
```

The document is read as text, HTML-style comments are stripped, and `<!-- image -->` markers are counted as extracted evidence metadata.

## Output

The command prints JSON similar to:

```json
{
  "control_id": "...",
  "control_title": "...",
  "domain": "...",
  "subdomain": "...",
  "evidence_code": "...",
  "evidence_description": "...",
  "document_name": "...",
  "present": true,
  "score_percentage": 85.0,
  "reasoning": "..."
}
```

## Notes

- The model is currently configured in [compliance_scorer.py](compliance_scorer.py).
- Evidence codes must exist in the hierarchy file or the script raises a `KeyError`.
- The repository also includes [TFC - Cyber Security Governance Committee (V1.6).md](TFC%20-%20Cyber%20Security%20Governance%20Committee%20%28V1.6%29.md) as source context.