import json
import os
import re
import openai
from json_repair import repair_json

JSON_FILE_PATH = os.path.join(os.path.dirname(__file__), "sama-csf-hierarchy-level3.json")

# Set VLLM_BASE_URL to point at a running vLLM server (e.g. http://localhost:8000/v1).
# When set, VLLM_MODEL selects the served model name (defaults to qwen3.6-27b-awq).
# When unset, falls back to OpenAI with OPENAI_API_KEY and MODEL_NAME (default gpt-4o).
_VLLM_BASE_URL = (os.environ.get("VLLM_BASE_URL") or "").strip()
_VLLM_MODEL    = (os.environ.get("VLLM_MODEL") or "qwen3.6-27b-awq").strip()
_OAI_MODEL     = (os.environ.get("MODEL_NAME") or "gpt-4o").strip()

MODEL = _VLLM_MODEL if _VLLM_BASE_URL else _OAI_MODEL

# Thinking mode off — model returns JSON directly without chain-of-thought preamble.
# _extract_json() still strips any stray </think> markers if present.
_EXTRA_BODY: dict = {"chat_template_kwargs": {"enable_thinking": False}} if _VLLM_BASE_URL else {}

# ── System prompt (timeless — no per-call variables) ──────────────────────────

_SYSTEM_PROMPT = """\
You are a compliance evidence evaluation assistant for the SAMA Cyber Security Framework.
**Task:** Evaluate whether the provided evidence satisfies the given requirement. Output **a single JSON** only.

---

# CORE PRINCIPLE
**If an auditor asked for this requirement, would they accept these files?** Judge by semantic intent, not keywords.

# KEY CONCEPT DISAMBIGUATIONS (read before classifying)

These compliance concepts are routinely confused. Treat them as distinct:

- **Risk Acceptance** (a business owner formally signs off on accepting a specific, identified risk, often via a Jira/ITSM ticket with approval workflow, approver name, date, status) is NOT the same as **Risk Appetite** (an organization-level document defining overall risk tolerance tiers and thresholds). Evidence of a signed-off specific risk acceptance DOES satisfy "signed business-owner acceptance form" requirements. Do NOT require a separate Risk Appetite policy document for acceptance-form requirements. **EXCEPTION for SAMA risk-acceptance controls (domain 3.2.1.x):** when the control itself is about the risk acceptance *process*, a formally approved ITSM/Jira risk acceptance workflow with multi-level governance sign-off (e.g. HoE → CTO → CPO) demonstrates predefined approval thresholds in operation and IS a PARTIAL_MATCH for Risk Appetite requirements — score evidence_strength 50-70 depending on how much threshold/tolerance detail is visible.
- **Charter** (establishes a function, committee, or role with mandate, authority, structure, reporting lines) overlaps heavily with **Strategy** (defines same authority, structure, roles, reporting for the same scope). A strategy document that covers those four elements IS a functional charter. Do NOT demand a document literally titled "Charter".
- **Policy** (mandatory requirements set by authority) overlaps with **Standard** (mandatory technical/procedural requirements). Either can satisfy the other.
- **Procedure** (step-by-step how-to) can be satisfied by an **operational report** that shows recurring execution of those steps with dates/metrics.
- **Register** (structured list with items, owners, dates, statuses) can be satisfied by a spreadsheet OR a periodic status report with the same shape.
- **Cybersecurity** is NOT the same as IT. Do not assume Cybersecurity is a subset of IT unless the evidence explicitly states so. IT-scoped documents, approvals, or allocations do not satisfy Cybersecurity-specific requirements unless they contain a clearly labeled, separate Cybersecurity section, line item, or scope.

# STEP 1 — Translate Requirement & Evidence into Questions
- **requirement_intent**: "The auditor is asking: ______?"
- **evidence_provides**: "These files collectively answer: ______?"
- **evaluation_path**: ARTIFACT | DOCUMENT | ACTIVITY_PROOF

# STEP 2 — Functional Equivalence (apply BEFORE classifying — do NOT over-audit)

Check these equivalences FIRST. If any match, classify as DIRECT_MATCH (or PARTIAL_MATCH if incomplete), not TYPE_MISMATCH.

**2A) Substance Over Label — these are DIRECT_MATCH, not TYPE_MISMATCH:**
- A committee charter that lists members, roles, composition, and reporting lines → IS evidence of **organizational structure/chart** for that committee. A charter defines the structure — it does not need to be a visual diagram. Score as DIRECT_MATCH.
- Strategy defining authority, structure, roles, reporting → serves as **Charter**
- Standard setting mandatory requirements → serves as **Policy**
- A document defining security gates, checkpoints, and controls for the development/deployment pipeline → IS a **Secure SDLC methodology standard** regardless of its title
- Operational report showing recurring execution (quarterly SLA reviews, access reviews) → proves **Procedure exists and is practiced**. A quarterly vendor SLA review with tracked metrics across multiple quarters IS evidence of an "SLA-monitoring procedure" — score as DIRECT_MATCH.
- A vendor SLA review tracking cloud provider uptime, incidents, and compliance metrics → IS evidence of **cloud compliance monitoring controls** in action
- Approved audit schedule with scopes, frequencies, responsibilities → serves as **Review procedure**
- Structured spreadsheet tracking items with dates, statuses, owners → IS a **Register**
- Bi-weekly/monthly report tracking threats with statuses and actions → IS a **Register**
- A vulnerability management process document that includes KPIs, scan frequencies, severity classifications, and remediation SLAs → at **L1-L2** this IS a **draft review report** (at L2 the process definition with effectiveness metrics is the review)
- An approved audit schedule that explicitly lists a specific security domain (e.g., "Physical & Environmental Security") as a recurring audit scope with defined frequency and governance sign-off → IS evidence that the organisation formally monitors and evaluates that domain — score as PARTIAL_MATCH (evidence_strength 50-65). If the package also includes a KPI/metrics report or executed audit findings for that same domain, upgrade to DIRECT_MATCH.
- A quarterly/annual KPI or KRI report that tracks effectiveness metrics for a specific security domain → IS an "effectiveness monitoring report" for that domain — score as DIRECT_MATCH when the metrics clearly map to the domain in the requirement.

**2B) Board-Approved Equivalence:**
RCC / Audit Committee / Executive Committee / Security Committee with board authority all count. Document control block with Approving Authority + Approval Date + Version = sufficient approval proof.

**2C) Digital = Physical:**
Jira/ServiceNow approvals with status/approver/date = signed forms. DocuSign/Signit = physical signature. ITSM tickets showing change records, risk acceptances, security reviews with approval status ARE formal records, not "informal screenshots." Specifically: a Jira/ITSM screenshot showing a change request with security validation steps, acceptance criteria, or security review sections IS a "change management record showing security review" — score as DIRECT_MATCH

**2D) Combined Governance:**
A "Risk & Compliance Committee Charter" with explicit cybersecurity mandate satisfies "Cyber Security Committee Charter."

**2E) Multi-File Packages — CRITICAL for "list" requirements:**
Multiple files = evaluate COLLECTIVELY as one package. First catalog what each file shows, then count distinct categories across ALL files:
- 8 files showing 5+ different monitoring tools (e.g., CIS compliance dashboards + IP reputation + SSL scans + vulnerability assessments + cloud security reports) = comprehensive list → **DIRECT_MATCH**, evidence_strength 80+
- 2 files from one narrow area (e.g., SSL scan + TLS scan = both certificate scanning) = incomplete list → PARTIAL_MATCH, evidence_strength ≤ 40
The files themselves ARE the list — each file is evidence of an implemented tool. Do not require a separate "list document."
- **Domain relevance in packages:** when the requirement is domain-specific (e.g., Physical Security, Third-Party, HR), only count files that address that domain. A cyber/technical security document (vulnerability scans, code KPIs) does NOT contribute to a Physical Security evaluation requirement even when included in the same package — assess it as non-contributing and score on the files that actually match the domain.

**2F) Maturity Level:**
At L1-L2: drafts, ad-hoc evidence, process docs with KPIs can satisfy "review report" requirements. At L3+: formal approval expected; process docs for register requirements = TYPE_MISMATCH.

# STEP 3 — Intent Alignment (after applying Step 2 equivalences)

Compare the two questions from Step 1 and classify:

**Intent Alignment:**
- **SAME_QUESTION** = evidence directly answers the requirement
- **RELATED_QUESTION** = partial overlap or close but not exact
- **DIFFERENT_QUESTION** = no meaningful overlap

**Semantic Match:**
- **DIRECT_MATCH** = SAME_QUESTION + functionally satisfies requirement (including via Step 2 equivalences)
- **PARTIAL_MATCH** = RELATED_QUESTION or missing key elements
- **TYPE_MISMATCH** = about the topic but wrong deliverable (process doc for register, schedule for report) AND not covered by any Step 2 equivalence
- **DOMAIN_MISMATCH** = different security domain (file references different SAMA CSF control)
- **UNRELATED** = different topic entirely or non-compliance content (receipts, memes)

**Hard caps on evidence_strength (0-100) — apply ONLY after confirming no Step 2 equivalence applies:**
- DIRECT_MATCH and complete → range 85-100
- PARTIAL_MATCH → range 40-80
- TYPE_MISMATCH → cap at range 15-40
- DOMAIN_MISMATCH or DIFFERENT_QUESTION → range 10-15
- UNRELATED → 0

# STEP 4 — Self-Check Before Locking Classification

Before you finalize the `semantic_match` label and apply a low cap:

1. If your draft is TYPE_MISMATCH: re-read Step 2A-2F and verify the evidence does NOT match any listed equivalence. If it does, upgrade to DIRECT_MATCH or PARTIAL_MATCH.
2. If your draft is DOMAIN_MISMATCH: verify the evidence is truly for a different SAMA CSF control. Generic security monitoring evidence that includes the requested domain is NOT DOMAIN_MISMATCH.
3. If you are looking at multiple files and drafting anything other than DIRECT_MATCH, re-read Step 2E and count distinct categories across all files. Multi-file packages count as the list.
4. If the requirement uses a governance term (Charter, Policy, Procedure, Register, Acceptance, Appetite), re-read the Key Concept Disambiguations section above before finalizing.

Only after this self-check can the hard cap from Step 3 be applied.

# STEP 5 — Build 5 Micro-Requirements (MR1..MR5)
Derive from the requirement intent. Each must be audit-checkable. At least one must be intent-defining (cannot be satisfied by wrong deliverable type).

# STEP 6 — Score MR1..MR5 (0, 3, or 5 each)
- 0 = not met | 3 = partially met | 5 = fully met
- Apply Step 2 equivalences before scoring.

# STEP 7 — Reliability (0-100)
- Formal approval present → 85-100
- Clear workflow/digital approvals → 75-90
- Undated/unclear screenshots → 40-70
- TYPE_MISMATCH/DOMAIN_MISMATCH → below 40
- UNRELATED → 0

# OUTPUT — STRICTLY WELL FORMATTED JSON ONLY

{
  "evidence_strength": 0,
  "reliability": 0,
  "semantic_analysis": {
    "requirement_intent": "",
    "evidence_provides": "",
    "intent_alignment": "",
    "semantic_match": "",
    "match_explanation": ""
  },
  "evaluation_path": "",
  "micro_requirements": [
    {"id": "MR1", "statement_en": "", "statement_ar": "", "met_score": 0, "evidence_snippet": ""},
    {"id": "MR2", "statement_en": "", "statement_ar": "", "met_score": 0, "evidence_snippet": ""},
    {"id": "MR3", "statement_en": "", "statement_ar": "", "met_score": 0, "evidence_snippet": ""},
    {"id": "MR4", "statement_en": "", "statement_ar": "", "met_score": 0, "evidence_snippet": ""},
    {"id": "MR5", "statement_en": "", "statement_ar": "", "met_score": 0, "evidence_snippet": ""}
  ],
  "explanation_en": "",
  "explanation_ar": "",
  "actions_needed_en": [],
  "actions_needed_ar": []
}
"""


def _extract_maturity_level(evidence_code: str) -> str:
    m = re.search(r"L(\d+)", evidence_code)
    return f"L{m.group(1)}" if m else "L3"


def _extract_json(raw: str) -> dict:
    """Extract first complete JSON object from raw text, handling think-blocks and fences."""
    # When thinking mode is on without a server-side reasoning parser, the model may
    # output its reasoning as plain text ending with </think> (no opening tag).
    # Strip everything up to and including the last </think>.
    if "</think>" in raw:
        raw = raw[raw.rindex("</think>") + len("</think>"):].strip()
    # Also strip any remaining <think>...</think> blocks (with opening tags)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Bracket-matching walk to extract the outermost {...}
    start = raw.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in LLM output: {raw!r}")
    depth = 0
    in_str = False
    esc = False
    candidate = None
    for i, ch in enumerate(raw[start:], start):
        if esc:
            esc = False
            continue
        if ch == "\\" and in_str:
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
        if not in_str:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = raw[start : i + 1]
                    break
    if candidate:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        # LLM produced malformed JSON (e.g. unescaped quotes in Arabic text) — repair it
        repaired = repair_json(candidate, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
    # Last resort: repair the full cleaned string
    repaired = repair_json(raw, return_objects=True)
    if isinstance(repaired, dict):
        return repaired
    raise ValueError(f"No valid JSON object found in LLM output: {raw!r}")


# ── Build lookup dicts at startup ─────────────────────────────────────────────

def _build_indexes(json_path: str) -> dict:
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

# ── OpenAI-compatible client (OpenAI or vLLM) ─────────────────────────────────

_api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()

if _VLLM_BASE_URL:
    _client = openai.OpenAI(base_url=_VLLM_BASE_URL, api_key="vllm")
else:
    _client = openai.OpenAI(api_key=_api_key)


# ── Prompt building ────────────────────────────────────────────────────────────

def _build_user_message(req: dict, documents: list[dict]) -> str:
    maturity = _extract_maturity_level(req["evidence_code"])
    file_list = "; ".join(d["doc_name"] for d in documents)

    context_block = (
        f"## Context\n"
        f"- **Framework:** 'Cyber Security Framework (CSF)'\n"
        f"- **Issuing Authority:** 'Saudi Arabian Monetary Authority (SAMA)'\n"
        f"- **Domain:** '{req['domain']}'\n"
        f"- **Subdomain:** '{req['subdomain']}'\n"
        f"- **Control:** '{req['control_code']} - {req['title']}'\n"
        f"- **Control Description:** '{req['description']}'\n"
        f"- **Guideline:** 'N/A'\n"
        f"- **Maturity Level:** '{maturity}'\n"
        f"- **Evidence Inventory:** '{file_list}'\n"
        f"\n"
        f"## Evidence Under Evaluation\n"
        f"- **Requirement Code:** '{req['evidence_code']}'\n"
        f"- **Requirement:** '{req['evidence_description']}'\n"
        f"- **Files ({len(documents)} total):** '{file_list}'\n"
    )

    docs_block = "\n## Document Content\n"
    for i, doc in enumerate(documents, 1):
        extra_section = ""
        if doc.get("doc_extra"):
            extra_section = f"\n  [Additional elements: {json.dumps(doc['doc_extra'])}]"
        docs_block += (
            f"\n--- Document {i}: {doc['doc_name']} ---\n"
            f"{doc['doc_text']}"
            f"{extra_section}\n"
        )

    return context_block + docs_block


# ── LLM call and result normalisation ─────────────────────────────────────────

def _call_llm(user_message: str) -> dict:
    response = _client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        extra_body=_EXTRA_BODY or None,
    )
    raw = response.choices[0].message.content.strip()
    return _extract_json(raw)


def _parse_llm_result(llm: dict) -> dict:
    evidence_strength = float(llm.get("evidence_strength", 0))
    return {
        "present": evidence_strength >= 60,
        "score_percentage": evidence_strength,
        "reasoning": llm.get("explanation_en", ""),
        "reliability": llm.get("reliability", 0),
        "semantic_analysis": llm.get("semantic_analysis", {}),
        "evaluation_path": llm.get("evaluation_path", ""),
        "micro_requirements": llm.get("micro_requirements", []),
        "explanation_en": llm.get("explanation_en", ""),
        "explanation_ar": llm.get("explanation_ar", ""),
        "actions_needed_en": llm.get("actions_needed_en", []),
        "actions_needed_ar": llm.get("actions_needed_ar", []),
    }


# ── Entry points ──────────────────────────────────────────────────────────────

def score_document(
    evidence_code: str,
    doc_name: str,
    doc_text: str,
    doc_extra: list[str] | None = None,
) -> dict:
    """Score a single document against a SAMA CSF evidence requirement."""
    if evidence_code not in _REQUIREMENT_INDEX:
        raise KeyError(f"Evidence code '{evidence_code}' not found in the SAMA CSF hierarchy.")

    req = _REQUIREMENT_INDEX[evidence_code]
    documents = [{"doc_name": doc_name, "doc_text": doc_text, "doc_extra": doc_extra}]
    user_msg = _build_user_message(req, documents)
    llm_result = _call_llm(user_msg)

    return {
        "control_id": req["control_code"],
        "control_title": req["title"],
        "domain": req["domain"],
        "subdomain": req["subdomain"],
        "evidence_code": evidence_code,
        "evidence_description": req["evidence_description"],
        "document_name": doc_name,
        **_parse_llm_result(llm_result),
    }


def score_documents(
    evidence_code: str,
    documents: list[dict],
) -> dict:
    """Score multiple documents collectively against one SAMA CSF evidence requirement."""
    if not documents:
        raise ValueError("At least one document must be provided.")
    if evidence_code not in _REQUIREMENT_INDEX:
        raise KeyError(f"Evidence code '{evidence_code}' not found in the SAMA CSF hierarchy.")

    req = _REQUIREMENT_INDEX[evidence_code]
    user_msg = _build_user_message(req, documents)
    llm_result = _call_llm(user_msg)

    return {
        "control_id": req["control_code"],
        "control_title": req["title"],
        "domain": req["domain"],
        "subdomain": req["subdomain"],
        "evidence_code": evidence_code,
        "evidence_description": req["evidence_description"],
        "document_names": [d["doc_name"] for d in documents],
        **_parse_llm_result(llm_result),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
# Single doc:   python compliance_scorer.py <evidence_code> <doc1>
# Multi-doc:    python compliance_scorer.py <evidence_code> <doc1> <doc2> ...

if __name__ == "__main__":
    import sys

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
