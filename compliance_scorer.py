import json
import os
import openai

JSON_FILE_PATH = os.path.join(os.path.dirname(__file__), "sama-csf-hierarchy-level3.json")
MODEL = "gpt-4o"

# ── Build lookup dicts at startup ─────────────────────────────────────────────

def _build_indexes(json_path: str) -> dict:
    """Returns requirement_index keyed by requirement code e.g. "SAMA-3.1.2-1-L3-1"."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    requirement_index = {}

    for domain in data.get("domains", []):
        for subdomain in domain.get("subDomains", []):
            for control in subdomain.get("controls", []):
                ctx = {
                    "domain": domain["nameEn"],
                    "subdomain": subdomain["nameEn"],
                    "title": control["titleEn"],
                    "description": control["descriptionEn"],
                    "control_code": control["code"],
                }
                for req in control.get("levels", [{}])[0].get("requirements", []):
                    requirement_index[req["code"]] = {
                        **ctx,
                        "evidence_code": req["code"],
                        "evidence_description": req["descriptionEn"],
                    }

    return requirement_index


_REQUIREMENT_INDEX = _build_indexes(JSON_FILE_PATH)

# ── OpenAI client ─────────────────────────────────────────────────────────────

_api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
_client = openai.OpenAI(api_key=_api_key)

# ── LLM scoring ───────────────────────────────────────────────────────────────

def _score_against_requirement(
    req: dict,
    doc_name: str,
    doc_text: str,
    doc_extra: list[str] | None,
) -> dict:
    system = (
        "You are a compliance analyst assessing whether a document satisfies a specific "
        "SAMA Cyber Security Framework evidence requirement. "
        "Analyse the document content carefully and return ONLY a JSON object with exactly "
        "three keys: "
        '"present" (boolean — true if the document adequately satisfies the requirement), '
        '"score" (integer 0-100 reflecting how well the document covers the requirement — '
        "100 = fully covered, 0 = not covered at all), "
        '"reasoning" (one sentence explaining your assessment). '
        "No preamble, no markdown fences."
    )

    extra_section = ""
    if doc_extra:
        extra_section = (
            f"\nAdditional extracted elements (stamps, signatures, images, etc.):\n"
            + json.dumps(doc_extra)
        )

    user = (
        f"Control: {req['title']} ({req['control_code']})\n"
        f"Domain: {req['domain']} > {req['subdomain']}\n"
        f"Control description: {req['description']}\n\n"
        f"Evidence requirement ({req['evidence_code']}):\n{req['evidence_description']}\n\n"
        f"Document name: {doc_name}\n"
        f"Extracted document text:\n{doc_text}"
        f"{extra_section}\n\n"
        "Does this document satisfy the evidence requirement above? Return JSON only."
    )

    response = _client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {raw!r}") from exc


def _score_multiple_against_requirement(
    req: dict,
    documents: list[dict],
) -> dict:
    """Score a collection of documents collectively against one requirement."""
    system = (
        "You are a compliance analyst assessing whether a set of documents, taken together, "
        "satisfies a specific SAMA Cyber Security Framework evidence requirement. "
        "Consider the documents as a combined evidence package — they may complement each other. "
        "Return ONLY a JSON object with exactly three keys: "
        '"present" (boolean — true if the documents collectively satisfy the requirement), '
        '"score" (integer 0-100 reflecting how well the combined evidence covers the requirement — '
        "100 = fully covered, 0 = not covered at all), "
        '"reasoning" (one sentence explaining your assessment of the combined evidence). '
        "No preamble, no markdown fences."
    )

    docs_section = ""
    for i, doc in enumerate(documents, 1):
        extra_section = ""
        if doc.get("doc_extra"):
            extra_section = (
                f"\n  Additional extracted elements: {json.dumps(doc['doc_extra'])}"
            )
        docs_section += (
            f"\n--- Document {i}: {doc['doc_name']} ---\n"
            f"{doc['doc_text']}"
            f"{extra_section}\n"
        )

    user = (
        f"Control: {req['title']} ({req['control_code']})\n"
        f"Domain: {req['domain']} > {req['subdomain']}\n"
        f"Control description: {req['description']}\n\n"
        f"Evidence requirement ({req['evidence_code']}):\n{req['evidence_description']}\n\n"
        f"Evidence package ({len(documents)} document(s)):{docs_section}\n"
        "Do these documents collectively satisfy the evidence requirement above? Return JSON only."
    )

    response = _client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {raw!r}") from exc


# ── Entry points ──────────────────────────────────────────────────────────────

def score_document(
    evidence_code: str,
    doc_name: str,
    doc_text: str,
    doc_extra: list[str] | None = None,
) -> dict:
    """Score a single document against a SAMA CSF evidence requirement.

    Args:
        evidence_code: the requirement code, e.g. "SAMA-3.1.1-1-L3-1"
        doc_name:      filename or display name of the document
        doc_text:      raw extracted text from the document
        doc_extra:     optional list of non-text elements (stamps, signatures, images, etc.)

    Returns:
        Result dict with score_percentage, present flag, and reasoning.
    """
    if evidence_code not in _REQUIREMENT_INDEX:
        raise KeyError(f"Evidence code '{evidence_code}' not found in the SAMA CSF hierarchy.")

    req = _REQUIREMENT_INDEX[evidence_code]

    llm_result = _score_against_requirement(req, doc_name, doc_text, doc_extra)

    return {
        "control_id": req["control_code"],
        "control_title": req["title"],
        "domain": req["domain"],
        "subdomain": req["subdomain"],
        "evidence_code": evidence_code,
        "evidence_description": req["evidence_description"],
        "document_name": doc_name,
        "present": llm_result.get("present", False),
        "score_percentage": float(llm_result.get("score", 0)),
        "reasoning": llm_result.get("reasoning", ""),
    }


def score_documents(
    evidence_code: str,
    documents: list[dict],
) -> dict:
    """Score multiple documents collectively against one SAMA CSF evidence requirement.

    All documents are evaluated as a combined evidence package, producing a single
    compliance score that reflects their collective coverage of the requirement.

    Args:
        evidence_code: the requirement code, e.g. "SAMA-3.1.1-1-L3-1"
        documents:     list of dicts, each with keys:
                         "doc_name"  (str)            — filename or display name
                         "doc_text"  (str)            — raw extracted text
                         "doc_extra" (list[str]|None) — optional non-text elements

    Returns:
        Result dict with score_percentage, present flag, reasoning, and document_names list.
    """
    if not documents:
        raise ValueError("At least one document must be provided.")

    if evidence_code not in _REQUIREMENT_INDEX:
        raise KeyError(f"Evidence code '{evidence_code}' not found in the SAMA CSF hierarchy.")

    req = _REQUIREMENT_INDEX[evidence_code]

    llm_result = _score_multiple_against_requirement(req, documents)

    return {
        "control_id": req["control_code"],
        "control_title": req["title"],
        "domain": req["domain"],
        "subdomain": req["subdomain"],
        "evidence_code": evidence_code,
        "evidence_description": req["evidence_description"],
        "document_names": [d["doc_name"] for d in documents],
        "present": llm_result.get("present", False),
        "score_percentage": float(llm_result.get("score", 0)),
        "reasoning": llm_result.get("reasoning", ""),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
# Single doc:   python compliance_scorer.py <evidence_code> <doc1>
# Multi-doc:    python compliance_scorer.py <evidence_code> <doc1> <doc2> ...

if __name__ == "__main__":
    import sys
    import re

    if len(sys.argv) < 3:
        print("Usage: python compliance_scorer.py <evidence_code> <document_path> [<document_path> ...]")
        sys.exit(1)

    evidence_code = sys.argv[1]
    doc_paths = sys.argv[2:]

    def _parse_doc(path: str) -> dict:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        image_tags = re.findall(r"<!--\s*image\s*-->", raw, flags=re.IGNORECASE)
        doc_extra = [f"{len(image_tags)} image placeholder(s) detected in document"] if image_tags else None
        doc_text = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL).strip()
        return {"doc_name": os.path.basename(path), "doc_text": doc_text, "doc_extra": doc_extra}

    if len(doc_paths) == 1:
        doc = _parse_doc(doc_paths[0])
        result = score_document(
            evidence_code=evidence_code,
            doc_name=doc["doc_name"],
            doc_text=doc["doc_text"],
            doc_extra=doc["doc_extra"],
        )
    else:
        documents = [_parse_doc(p) for p in doc_paths]
        result = score_documents(evidence_code=evidence_code, documents=documents)

    print(json.dumps(result, indent=2, ensure_ascii=False))
