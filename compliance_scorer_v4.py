import json
import os
import re
import openai
from json_repair import repair_json

PROMPT_VERSION = "v4"

JSON_FILE_PATH = os.path.join(os.path.dirname(__file__), "sama-csf-hierarchy-level3.json")

_VLLM_BASE_URL = (os.environ.get("VLLM_BASE_URL") or "").strip()
_VLLM_MODEL    = (os.environ.get("VLLM_MODEL") or "qwen3.6-27b-awq").strip()
_OAI_MODEL     = (os.environ.get("MODEL_NAME") or "gpt-4o").strip()

MODEL = _VLLM_MODEL if _VLLM_BASE_URL else _OAI_MODEL

_EXTRA_BODY: dict = {"chat_template_kwargs": {"enable_thinking": False}} if _VLLM_BASE_URL else {}

# ══════════════════════════════════════════════════════════════════════════════
# PROMPT V2 — edit this block to test prompt changes
# Compare results against benchmark_results_v1_<model>.json (from compliance_scorer.py)
# ══════════════════════════════════════════════════════════════════════════════

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

# STRICT TYPE-MISMATCH RULES (apply these BEFORE any equivalence check)

These document types are NEVER functionally equivalent, regardless of governance language or approvals present:

- An **operational process document** (e.g. Vulnerability Management Process, Incident Response Procedure, Change Management Process) is NOT a Charter, NOT an Org Chart, and NOT a Risk Appetite document — even if it is RCC-approved and mentions roles. Score as TYPE_MISMATCH, evidence_strength ≤ 35.
  **Exception for SAMA 3.2.1.x controls only:** a formally approved ITSM/Jira risk acceptance workflow with multi-level governance sign-off (HoE → CTO → CPO) IS a PARTIAL_MATCH (evidence_strength 50-70) for Risk Appetite requirements — see KEY CONCEPT DISAMBIGUATIONS above.
- A **technical security standard or policy** (e.g. Cloud Computing Standard, Password Policy, Encryption Standard) is NOT an Org Chart and NOT a Charter — even if it names a VP or approving authority. Score as TYPE_MISMATCH, evidence_strength ≤ 35.
- A **Static Application Security Testing (SAST) tool or architecture** is NOT a Penetration Test report. SAST = automated code analysis during development. Pentest = active external attack simulation. Score as TYPE_MISMATCH, evidence_strength ≤ 25.
- An **organizational chart** is NOT a Risk Appetite document, NOT a Policy, and NOT a Risk Register — even if signed by the CEO. Score as DOMAIN_MISMATCH or TYPE_MISMATCH, evidence_strength ≤ 15.

**IMPORTANT — Multi-file packages:** These strict rules apply when the ONLY evidence submitted is a mismatching document type. In a multi-file package, the presence of one non-matching document does NOT lower the overall package score — exclude it as non-contributing and evaluate the remaining files per Step 2E. Only fire a strict rule against the whole package if ALL files are of the mismatching type.

# STEP 1 — Translate Requirement & Evidence into Questions
- **requirement_intent**: "The auditor is asking: ______?"
- **evidence_provides**: "These files collectively answer: ______?"
- **evaluation_path**: ARTIFACT | DOCUMENT | ACTIVITY_PROOF

# STEP 2 — Functional Equivalence (apply AFTER confirming no Strict Type-Mismatch rule fires)

Check these equivalences. If any match, classify as DIRECT_MATCH (or PARTIAL_MATCH if incomplete).

**2A) Substance Over Label — these are DIRECT_MATCH, not TYPE_MISMATCH:**
- A committee charter that lists members, roles, composition, and reporting lines → IS evidence of **organizational structure/chart** for that committee. A charter defines the structure — it does not need to be a visual diagram. Score as DIRECT_MATCH.
- Strategy defining authority, structure, roles, reporting → serves as **Charter**
- Standard setting mandatory requirements → serves as **Policy**
- A document defining security gates, checkpoints, and controls for the development/deployment pipeline → IS a **Secure SDLC methodology standard** regardless of its title
- Operational report showing recurring execution (quarterly SLA reviews, access reviews) → proves **Procedure exists and is practiced**. A quarterly vendor SLA review with tracked metrics across multiple quarters IS evidence of an "SLA-monitoring procedure" — score as DIRECT_MATCH.
- A vendor SLA review tracking cloud provider uptime, incidents, and compliance metrics → IS evidence of **cloud compliance monitoring controls** in action
- A policy document containing a version metadata block (Version: X.X, Approval Date, Last Review Date, Next Review Date) → IS a **version history** for that policy. A separate standalone "version history log" file is NOT required. The version metadata embedded in the document header satisfies "periodic review with version tracking" requirements — score as DIRECT_MATCH if the metadata is present and shows governance approval.
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
  **Example (Physical Security effectiveness):** a package containing [Internal Audit Schedule explicitly listing "Physical & Environmental Security" as annual audit scope, RCC-approved] + [KPI/KRI report tracking physical security access reviews] = DIRECT_MATCH (evidence_strength 80+) — the schedule proves periodic evaluation is planned and governed, the KPI proves it is measured. A third file in the same package (e.g. Vulnerability Management Process) is cyber-domain, non-contributing — do not penalise the package for its presence.
  **Counter-example:** [Audit Schedule] + [Org Chart] = NOT sufficient. An org chart proves organisational structure — it does NOT prove measurement or effectiveness monitoring. The supplementary document must be a metrics or measurement artifact (KPI dashboard, KRI tracker, audit findings report, or operational data with targets). If the only non-audit-schedule file is an org chart, score the package on the audit schedule alone (PARTIAL_MATCH, evidence_strength 50-65).

**2F) Maturity Level:**
At L1-L2: drafts, ad-hoc evidence, process docs with KPIs can satisfy "review report" requirements. At L3+: formal approval expected; process docs for register requirements = TYPE_MISMATCH.

# STEP 3 — Intent Alignment (after applying Steps above)

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

**Hard caps on evidence_strength (0-100) — these are ABSOLUTE CEILINGS:**
- DIRECT_MATCH and complete → range 85-100
- PARTIAL_MATCH → range 40-80
- TYPE_MISMATCH → **hard cap 35** (do not exceed under any circumstance)
- DOMAIN_MISMATCH or DIFFERENT_QUESTION → **hard cap 15**
- UNRELATED → 0

# STEP 4 — Self-Check Before Locking Classification

Before you finalize the `semantic_match` label and apply a low cap:

1. Did a **Strict Type-Mismatch rule** (at the top) fire? If yes, TYPE_MISMATCH is confirmed — do NOT upgrade to PARTIAL_MATCH because the document has governance language or mentions roles. Apply the hard cap.
2. If your draft is TYPE_MISMATCH: re-read Step 2A-2F and verify the evidence does NOT match any listed equivalence. If it does, upgrade. If it does not, keep TYPE_MISMATCH and apply the cap.
3. If your draft is DOMAIN_MISMATCH: verify the evidence is truly for a different SAMA CSF control. Generic security monitoring evidence that includes the requested domain is NOT DOMAIN_MISMATCH.
4. If you are looking at multiple files and drafting anything other than DIRECT_MATCH, re-read Step 2E and count distinct categories across all files. Multi-file packages count as the list.
5. If the requirement uses a governance term (Charter, Policy, Procedure, Register, Acceptance, Appetite), re-read the Key Concept Disambiguations section above before finalizing.

Only after this self-check can the hard cap from Step 3 be applied.

# STEP 5 — Build 5 Micro-Requirements (MR1..MR5)
Derive from the requirement intent. Each must be audit-checkable. At least one must be intent-defining (cannot be satisfied by wrong deliverable type).

# STEP 6 — Score MR1..MR5 (0, 3, or 5 each)
- 0 = not met | 3 = partially met | 5 = fully met
- Apply Step 2 equivalences before scoring.
- If a Strict Type-Mismatch rule fired for this document, all MRs that require the correct deliverable type must score 0.

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

# ══════════════════════════════════════════════════════════════════════════════


def _extract_maturity_level(evidence_code: str) -> str:
    m = re.search(r"L(\d+)", evidence_code)
    return f"L{m.group(1)}" if m else "L3"


def _extract_json(raw: str) -> dict:
    if "</think>" in raw:
        raw = raw[raw.rindex("</think>") + len("</think>"):].strip()
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
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
        repaired = repair_json(candidate, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
    repaired = repair_json(raw, return_objects=True)
    if isinstance(repaired, dict):
        return repaired
    raise ValueError(f"No valid JSON object found in LLM output: {raw!r}")


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

_api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()

if _VLLM_BASE_URL:
    _client = openai.OpenAI(base_url=_VLLM_BASE_URL, api_key="vllm")
else:
    _client = openai.OpenAI(api_key=_api_key)


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


def _call_llm(user_message: str) -> dict:
    response = _client.chat.completions.create(
        model=MODEL,
        max_tokens=2048,
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


def score_document(
    evidence_code: str,
    doc_name: str,
    doc_text: str,
    doc_extra: list[str] | None = None,
) -> dict:
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
