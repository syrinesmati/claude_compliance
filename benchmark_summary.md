# SAMA CSF Compliance Scorer — LLM Benchmark Summary

**Date:** 2026-06-28  
**Evaluated by:** syrine@techtroll.co  
**Framework:** Saudi Arabian Monetary Authority (SAMA) Cyber Security Framework  
**Scorer:** `compliance_scorer.py` — 7-step production scoring prompt  
**Inference backend:** vLLM 0.22.1, OpenAI-compatible API (port 8000)

---

## 1. Overview

Six open-source LLMs were benchmarked as potential replacements for GPT-4o in a SAMA CSF compliance scoring pipeline. Each model was evaluated across 6 test cases, each with a **Success** evidence set (correct, compliant documents) and a **Failure** evidence set (wrong or non-compliant documents).

A test case is **PASS** only when:
- **Success set** → `evidence_strength ≥ 60` (present = YES)
- **Failure set** → `evidence_strength < 60` (present = NO)

Both conditions must hold. A model that scores failure evidence above 60 fails the test case even if it scored success evidence correctly.

---

## 2. Model Inventory

| # | Model | HF ID | Quant | Context | Notes |
|---|-------|--------|-------|---------|-------|
| 1 | **Qwen3.6-27B-AWQ** | `cyankiwi/Qwen3.6-27B-AWQ-INT4` | AWQ INT4 | 65536 | Thinking OFF |
| 2 | **Qwen3-30B-MoE-FP8** | `Qwen/Qwen3-30B-A3B-FP8` | FP8 MoE | 32768 | Thinking OFF |
| 3 | **Gemma4-26B-MoE-AWQ** | `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit` | AWQ 4-bit MoE | 32768 | — |
| 4 | **Qwen3.5-9B-BF16** | `Qwen/Qwen3.5-9B` | BF16 | 65536 | Thinking OFF |
| 5 | **Qwen3-32B-AWQ** | `Qwen/Qwen3-32B-AWQ` | AWQ | 32768 | Thinking OFF |
| 6 | **Gemma3-12B-BF16** | `unsloth/gemma-3-12b-it` | BF16 | 65536 | Note ¹ |

> **¹ Gemma3-12B-BF16:** The originally requested model `google/gemma-4-12b-it` uses the new `Gemma4UnifiedForConditionalGeneration` architecture (multimodal) which vLLM 0.22.1 does not support. The official `google/gemma-3-12b-it` is gated (no token access). `unsloth/gemma-3-12b-it` (BF16, Gemma 3 12B architecture) was used instead.

**Common settings for all runs:**
- `max_tokens = 2048`
- `enable_thinking = False` (Qwen3 models via `chat_template_kwargs`)
- `temperature` = model default
- `present` threshold: `evidence_strength ≥ 60`

---

## 3. Test Cases

| Code | Short Name | Requirement Intent |
|------|-----------|-------------------|
| SAMA-3.1.1-5-L3-1 | TC1 Cyber Charter | Formally approved Cyber Security Function Charter (or functional equivalent) |
| SAMA-3.1.1-5-L3-2 | TC2 Org Structure | Cyber Security Function established as a separate organisational unit with reporting lines |
| SAMA-3.1.3-2-L3-1 | TC3 Policy Review | Cyber Security Policy with documented, periodic version review history |
| SAMA-3.2.1.3-3-L3-1 | TC4 Risk Appetite | Approved Risk Appetite document or formally governed risk-acceptance process |
| SAMA-3.2.4-2-L3-2 | TC5 Pentest | Annual third-party penetration testing of internet-facing / customer-facing systems |
| SAMA-3.3.2-2-L3-1 | TC6 Phys Security | Periodic evaluation of Physical & Environmental Security process effectiveness |

### Evidence Sets

**TC1 — Cyber Charter**
- Success: `Lean CyberSecurity Strategy v4 2025.docx-3.md` (strategy covering mandate, roles, governance — accepted as functional charter)
- Failure: `Vulnerability_Management_Process.md` (operational process doc — wrong deliverable type)

**TC2 — Org Structure**
- Success: `Signed Org chart - SAMA.md` (DocuSigned org chart, CS function reporting to CEO)
- Failure: `Cloud Computing Standard v2.0.docx.md` (technical security standard — not an org chart)

**TC3 — Policy Review**
- Success: `Infrastructure Security Standard v2.docx.md` + `Lean Tech Information Security Policy v4.docx-3.md` + `Lean_Password_Policy.docx-3.md` (policy documents with version numbers, approval dates, review schedules)
- Failure: `Signed Org chart - SAMA.md` (org chart — completely unrelated)

**TC4 — Risk Appetite / Acceptance**
- Success: `Risk acceptance evidence1.md` + `risk acceptance flow.md` (Jira risk-acceptance ticket + multi-level approval workflow HoE→CTO→CPO)
- Failure: `Signed Org chart - SAMA.md` (org chart — unrelated)
- Note: The prompt includes a SAMA 3.2.1.x exception: a formally governed ITSM risk-acceptance workflow IS a PARTIAL_MATCH for Risk Appetite (score 50–70).

**TC5 — Pentest**
- Success: `3rd party pentesting report Nov 2024 KSA.md` + `Lean Technologies (KSA) Penetration Testing Report Nov-Dec 2025.md` (two annual 3rd-party pentest reports)
- Failure: `WhatsApp Image 2026-02-17 at 4.08.39 PM.md` (P-SAST architecture diagram — SAST ≠ pentest)

**TC6 — Physical Security Effectiveness**
- Success: `Live 2025 - Lean Tech Internal Audit Schedule V7 (2)_1.md` + `SecurityCompliance__KPIs__KRIs_ (1)_1.md` + `Vulnerability_Management_Process (2)_1.md`
- Failure: `Live 2025 - Lean Tech Internal Audit Schedule V7 (2)_1.md` + `Signed Org chart - SAMA.md`
- Note: TC6 is the hardest case. The success package is ambiguous (same audit schedule, cyber-focused KPIs, vuln mgmt process). The failure package contains the same audit schedule — models must distinguish governance planning from an actual evaluation report, and must not count cyber/technical docs toward a physical security domain requirement.

---

## 4. Results Summary

### 4.1 Pass/Fail Matrix (S = Success score, F = Failure score)

| Test Case | Qwen3.6-27B-AWQ | Qwen3-30B-MoE-FP8 | Gemma4-26B-MoE-AWQ | Qwen3.5-9B-BF16 | Qwen3-32B-AWQ | Gemma3-12B-BF16 |
|-----------|:-:|:-:|:-:|:-:|:-:|:-:|
| TC1 Cyber Charter | ✅ 95%/20% | ✅ 85%/40% | ✅ 85%/15% | ✅ 60%/0% | ❌ 95%/70% | ❌ 85%/95% |
| TC2 Org Structure | ✅ 90%/20% | ✅ 85%/30% | ✅ 95%/0% | ✅ 95%/0% | ✅ 95%/0% | ❌ 95%/85% |
| TC3 Policy Review | ✅ 65%/0% | ❌ 55%/20% | ✅ 85%/0% | ✅ 95%/0% | ✅ 85%/0% | ✅ 85%/40% |
| TC4 Risk Appetite | ❌ 55%/0% | ✅ 85%/25% | ❌ 45%/0% | ✅ 60%/0% | ✅ 80%/0% | ❌ 85%/60% |
| TC5 Pentest | ✅ 92%/0% | ✅ 75%/35% | ✅ 95%/0% | ✅ 95%/0% | ✅ 90%/15% | ❌ 85%/85% |
| TC6 Phys Security | ❌ 55%/60% | ❌ 50%/50% | ✅ 85%/15% | ❌ 20%/25% | ❌ 85%/70% | ❌ 95%/85% |
| **PASS COUNT** | **4/6** | **4/6** | **5/6** | **5/6** | **4/6** | **1/6** |
| **Avg Success** | 75.3% | 72.5% | 81.7% | 70.8% | 88.3% | 88.3% |
| **Avg Failure** ↓ | 16.7% | 33.3% | **5.0%** | **4.2%** | 25.8% | 75.0% |

### 4.2 Ranking

| Rank | Model | Pass | Avg Success | Avg Failure | Verdict |
|------|-------|:----:|:-----------:|:-----------:|---------|
| 🥇 1 | Gemma4-26B-MoE-AWQ | **5/6** | 81.7% | **5.0%** | Best overall — high success, lowest failure leakage |
| 🥇 1 | Qwen3.5-9B-BF16 | **5/6** | 70.8% | **4.2%** | Tied 1st — most conservative, sharpest discrimination |
| 🥉 3 | Qwen3.6-27B-AWQ | 4/6 | 75.3% | 16.7% | Good discrimination, fails TC4 (below threshold) & TC6 |
| 4 | Qwen3-32B-AWQ | 4/6 | 88.3% | 25.8% | Highest raw confidence, too lenient on failures |
| 4 | Qwen3-30B-MoE-FP8 | 4/6 | 72.5% | 33.3% | Fails TC3 (score too low) & TC6 |
| 6 | Gemma3-12B-BF16 | 1/6 | 88.3% | 75.0% | Scores everything high — cannot distinguish failures |

---

## 5. Per-Test-Case Analysis

### TC1 — Cyber Security Function Charter (SAMA-3.1.1-5-L3-1)

**Core challenge:** The success doc is titled "Strategy" not "Charter". The prompt's Step 2A rule (substance over label) must fire to accept it. The failure doc (Vuln Mgmt Process) mentions governance and RCC approval — lenient models score it as a partial charter.

| Model | Verdict | Success | Failure | Notes |
|-------|:-------:|:-------:|:-------:|-------|
| Qwen3.6-27B-AWQ | ✅ | 95% DIRECT | 20% TYPE_MISMATCH | Sharp |
| Qwen3-30B-MoE-FP8 | ✅ | 85% DIRECT | 40% PARTIAL | Acceptable |
| Gemma4-26B-MoE-AWQ | ✅ | 85% DIRECT | 15% DOMAIN_MISMATCH | Sharp |
| Qwen3.5-9B-BF16 | ✅ | 60% PARTIAL | 0% TYPE_MISMATCH | Conservative on success |
| Qwen3-32B-AWQ | ❌ | 95% DIRECT | **70% PARTIAL** | Failure too high |
| Gemma3-12B-BF16 | ❌ | 85% DIRECT | **95% DIRECT** | Completely wrong — vuln mgmt doc treated as charter |

---

### TC2 — Cyber Security Organisational Structure (SAMA-3.1.1-5-L3-2)

**Core challenge:** Failure doc is a technical cloud standard — should be an obvious TYPE_MISMATCH. Gemma3-12B incorrectly treats it as structural evidence.

| Model | Verdict | Success | Failure | Notes |
|-------|:-------:|:-------:|:-------:|-------|
| Qwen3.6-27B-AWQ | ✅ | 90% DIRECT | 20% TYPE_MISMATCH | |
| Qwen3-30B-MoE-FP8 | ✅ | 85% DIRECT | 30% PARTIAL | |
| Gemma4-26B-MoE-AWQ | ✅ | 95% DIRECT | 0% DOMAIN_MISMATCH | Perfect |
| Qwen3.5-9B-BF16 | ✅ | 95% DIRECT | 0% TYPE_MISMATCH | Perfect |
| Qwen3-32B-AWQ | ✅ | 95% DIRECT | 0% TYPE_MISMATCH | Perfect |
| Gemma3-12B-BF16 | ❌ | 95% DIRECT | **85% DIRECT** | Cloud standard treated as org structure evidence |

---

### TC3 — Cyber Security Policy Version History (SAMA-3.1.3-2-L3-1)

**Core challenge:** Success docs are policy documents with version history metadata. Failure is an org chart — totally unrelated. Qwen3-30B-MoE-FP8 under-scores the success set (55% → below threshold).

| Model | Verdict | Success | Failure | Notes |
|-------|:-------:|:-------:|:-------:|-------|
| Qwen3.6-27B-AWQ | ✅ | 65% PARTIAL | 0% UNRELATED | Success score barely passes |
| Qwen3-30B-MoE-FP8 | ❌ | **55% PARTIAL** | 20% TYPE_MISMATCH | Success below threshold |
| Gemma4-26B-MoE-AWQ | ✅ | 85% DIRECT | 0% UNRELATED | |
| Qwen3.5-9B-BF16 | ✅ | 95% DIRECT | 0% TYPE_MISMATCH | Best |
| Qwen3-32B-AWQ | ✅ | 85% DIRECT | 0% TYPE_MISMATCH | |
| Gemma3-12B-BF16 | ✅ | 85% DIRECT | 40% PARTIAL | Failure too close to threshold |

---

### TC4 — Risk Appetite / Acceptance (SAMA-3.2.1.3-3-L3-1)

**Core challenge:** The evidence (Jira risk-acceptance ticket + multi-level workflow) is NOT a Risk Appetite policy document but IS the correct governance artifact for this specific SAMA control. The prompt has an explicit exception for SAMA 3.2.1.x controls. Models that ignore the exception score it 15–45%. Models that apply it score 60–85%.

| Model | Verdict | Success | Failure | Notes |
|-------|:-------:|:-------:|:-------:|-------|
| Qwen3.6-27B-AWQ | ❌ | **55% PARTIAL** | 0% UNRELATED | Exception not fully applied — below threshold |
| Qwen3-30B-MoE-FP8 | ✅ | 85% DIRECT | 25% TYPE_MISMATCH | Exception applied correctly |
| Gemma4-26B-MoE-AWQ | ❌ | **45% TYPE_MISMATCH** | 0% UNRELATED | Strict: "Risk Acceptance ≠ Risk Appetite" |
| Qwen3.5-9B-BF16 | ✅ | 60% PARTIAL | 0% TYPE_MISMATCH | Barely passes with exception |
| Qwen3-32B-AWQ | ✅ | 80% PARTIAL | 0% DOMAIN_MISMATCH | Good exception reasoning |
| Gemma3-12B-BF16 | ❌ | 85% DIRECT | **60% PARTIAL** | Scores org chart as partial risk appetite evidence |

---

### TC5 — Annual Penetration Testing (SAMA-3.2.4-2-L3-2)

**Core challenge:** Failure doc is a P-SAST architecture diagram — SAST ≠ penetration testing. Most models handle this well. Qwen3-30B-MoE-FP8 scores the failure at 35% (borderline). Gemma3-12B scores it 85%.

| Model | Verdict | Success | Failure | Notes |
|-------|:-------:|:-------:|:-------:|-------|
| Qwen3.6-27B-AWQ | ✅ | 92% DIRECT | 0% TYPE_MISMATCH | |
| Qwen3-30B-MoE-FP8 | ✅ | 75% DIRECT | 35% PARTIAL | Failure score close to threshold |
| Gemma4-26B-MoE-AWQ | ✅ | 95% DIRECT | 0% DOMAIN_MISMATCH | |
| Qwen3.5-9B-BF16 | ✅ | 95% DIRECT | 0% TYPE_MISMATCH | |
| Qwen3-32B-AWQ | ✅ | 90% DIRECT | 15% DOMAIN_MISMATCH | |
| Gemma3-12B-BF16 | ❌ | 85% DIRECT | **85% PARTIAL** | SAST diagram treated as partial pentest evidence |

---

### TC6 — Physical Security Effectiveness Evaluation (SAMA-3.3.2-2-L3-1)

**Core challenge:** The hardest test case. Only Gemma4-26B passes it. Issues:
1. Both success and failure packages contain the same audit schedule — models must weigh the other documents
2. Success package contains a Vuln Mgmt Process (cyber domain) and cyber-focused KPIs — the domain relevance rule (Step 2E) must fire to not over-count these
3. The difference between the two sets is subtle: success has KPI/KRI metrics (partial effectiveness evidence) while failure only has the schedule and org chart
4. Several models score both sets similarly (50/50 or 85/70) — they can't distinguish planning from evaluation

| Model | Verdict | Success | Failure | Notes |
|-------|:-------:|:-------:|:-------:|-------|
| Qwen3.6-27B-AWQ | ❌ | 55% PARTIAL | **60% PARTIAL** | Failure higher than success |
| Qwen3-30B-MoE-FP8 | ❌ | 50% PARTIAL | 50% PARTIAL | Identical scores — no discrimination |
| Gemma4-26B-MoE-AWQ | ✅ | **85% DIRECT** | **15% TYPE_MISMATCH** | Only model to pass — domain relevance rule applied |
| Qwen3.5-9B-BF16 | ❌ | **20% PARTIAL** | 25% PARTIAL | Under-scores success severely |
| Qwen3-32B-AWQ | ❌ | 85% DIRECT | **70% PARTIAL** | Failure too high |
| Gemma3-12B-BF16 | ❌ | 95% DIRECT | **85% PARTIAL** | Audit schedule + org chart scored as evaluation evidence |

---

## 6. Key Findings

### What causes failures

| Root Cause | Affected Models | TC |
|-----------|----------------|----|
| **Too lenient on failures** — models over-generalize partial evidence | Qwen3-32B-AWQ, Gemma3-12B-BF16, Qwen3-30B-MoE-FP8 | TC1, TC2, TC5, TC6 |
| **Exception rule not applied** — "Risk Acceptance ≠ Risk Appetite" too strict | Gemma4-26B-MoE-AWQ, Qwen3.6-27B-AWQ | TC4 |
| **Success score below threshold** — model under-scores correct evidence | Qwen3.5-9B-BF16 (TC6), Qwen3-30B-MoE-FP8 (TC3), Qwen3.6-27B-AWQ (TC4) | TC3, TC4, TC6 |
| **Domain relevance not enforced** — cyber docs counted for physical security | All except Gemma4-26B | TC6 |

### TC6 is the hardest
TC6 has never been solved by any model except Gemma4-26B. The underlying issue is that the test data is genuinely ambiguous — the success package contains mostly cyber-domain documents (vuln mgmt process, cyber KPIs) with only an audit schedule showing physical security is planned. A correct auditor judgment requires applying Step 2E (domain relevance) strictly and recognising that a KPI/KRI report mentioning physical security access is meaningful evidence.

### Model size ≠ quality
The 9B BF16 model (Qwen3.5-9B) matches the 26B MoE model in pass rate and has the best failure discrimination (avg 4.2%). The 32B AWQ and 12B BF16 models (both avg success 88.3%) have the worst failure discrimination.

---

## 7. Recommendation

**Production use:** `Gemma4-26B-MoE-AWQ` or `Qwen3.5-9B-BF16`

- Gemma4-26B-MoE-AWQ: best overall, especially for domain-specific discrimination (TC6). One weak spot: TC4 (doesn't apply the SAMA risk-acceptance exception).
- Qwen3.5-9B-BF16: tied 1st, best failure discrimination, fastest inference. Conservative on success scores (may under-score borderline evidence).

**Avoid:** Gemma3-12B-BF16 (1/6, scores almost everything high).

**Prompt improvements still needed:**
- TC6: strengthen the physical-security domain relevance rule — add explicit examples of what counts vs. what doesn't
- TC4: the exception clause is partially working; consider making it more explicit with a concrete example of "multi-level ITSM workflow = 60%"
- TC1: Qwen3-32B needs a stronger TYPE_MISMATCH penalty for operational process docs

---

## 8. Scoring Prompt (Full)

The prompt below is the `_SYSTEM_PROMPT` used in `compliance_scorer.py`. The user message is assembled by `_build_user_message()` which injects the SAMA CSF requirement metadata and full document text at call time.

```
You are a compliance evidence evaluation assistant for the SAMA Cyber Security Framework.
**Task:** Evaluate whether the provided evidence satisfies the given requirement. Output **a single JSON** only.

---

# CORE PRINCIPLE
**If an auditor asked for this requirement, would they accept these files?** Judge by semantic intent, not keywords.

# KEY CONCEPT DISAMBIGUATIONS (read before classifying)

These compliance concepts are routinely confused. Treat them as distinct:

- **Risk Acceptance** (a business owner formally signs off on accepting a specific, identified risk, often via
  a Jira/ITSM ticket with approval workflow, approver name, date, status) is NOT the same as **Risk Appetite**
  (an organization-level document defining overall risk tolerance tiers and thresholds). Evidence of a signed-off
  specific risk acceptance DOES satisfy "signed business-owner acceptance form" requirements. Do NOT require a
  separate Risk Appetite policy document for acceptance-form requirements.
  **EXCEPTION for SAMA risk-acceptance controls (domain 3.2.1.x):** when the control itself is about the risk
  acceptance *process*, a formally approved ITSM/Jira risk acceptance workflow with multi-level governance sign-off
  (e.g. HoE → CTO → CPO) demonstrates predefined approval thresholds in operation and IS a PARTIAL_MATCH for
  Risk Appetite requirements — score evidence_strength 50-70 depending on how much threshold/tolerance detail
  is visible.

- **Charter** (establishes a function, committee, or role with mandate, authority, structure, reporting lines)
  overlaps heavily with **Strategy** (defines same authority, structure, roles, reporting for the same scope).
  A strategy document that covers those four elements IS a functional charter. Do NOT demand a document literally
  titled "Charter".

- **Policy** (mandatory requirements set by authority) overlaps with **Standard** (mandatory technical/procedural
  requirements). Either can satisfy the other.

- **Procedure** (step-by-step how-to) can be satisfied by an **operational report** that shows recurring execution
  of those steps with dates/metrics.

- **Register** (structured list with items, owners, dates, statuses) can be satisfied by a spreadsheet OR a
  periodic status report with the same shape.

- **Cybersecurity** is NOT the same as IT. Do not assume Cybersecurity is a subset of IT unless the evidence
  explicitly states so. IT-scoped documents, approvals, or allocations do not satisfy Cybersecurity-specific
  requirements unless they contain a clearly labeled, separate Cybersecurity section, line item, or scope.

# STEP 1 — Translate Requirement & Evidence into Questions
- **requirement_intent**: "The auditor is asking: ______?"
- **evidence_provides**: "These files collectively answer: ______?"
- **evaluation_path**: ARTIFACT | DOCUMENT | ACTIVITY_PROOF

# STEP 2 — Functional Equivalence (apply BEFORE classifying — do NOT over-audit)

Check these equivalences FIRST. If any match, classify as DIRECT_MATCH (or PARTIAL_MATCH if incomplete),
not TYPE_MISMATCH.

**2A) Substance Over Label — these are DIRECT_MATCH, not TYPE_MISMATCH:**
- A committee charter that lists members, roles, composition, and reporting lines → IS evidence of
  **organizational structure/chart** for that committee.
- Strategy defining authority, structure, roles, reporting → serves as **Charter**
- Standard setting mandatory requirements → serves as **Policy**
- A document defining security gates, checkpoints, and controls for the development/deployment pipeline →
  IS a **Secure SDLC methodology standard** regardless of its title
- Operational report showing recurring execution (quarterly SLA reviews, access reviews) → proves
  **Procedure exists and is practiced**
- A quarterly vendor SLA review with tracked metrics across multiple quarters IS evidence of an
  "SLA-monitoring procedure" — score as DIRECT_MATCH
- A vendor SLA review tracking cloud provider uptime, incidents, and compliance metrics → IS evidence of
  **cloud compliance monitoring controls** in action
- Approved audit schedule with scopes, frequencies, responsibilities → serves as **Review procedure**
- Structured spreadsheet tracking items with dates, statuses, owners → IS a **Register**
- Bi-weekly/monthly report tracking threats with statuses and actions → IS a **Register**
- A vulnerability management process document that includes KPIs, scan frequencies, severity
  classifications, and remediation SLAs → at **L1-L2** this IS a **draft review report**
- An approved audit schedule that explicitly lists a specific security domain (e.g., "Physical &
  Environmental Security") as a recurring audit scope with defined frequency and governance sign-off →
  IS evidence that the organisation formally monitors and evaluates that domain — score as PARTIAL_MATCH
  (evidence_strength 50-65). If the package also includes a KPI/metrics report or executed audit findings
  for that same domain, upgrade to DIRECT_MATCH.
- A quarterly/annual KPI or KRI report that tracks effectiveness metrics for a specific security domain →
  IS an "effectiveness monitoring report" for that domain — score as DIRECT_MATCH when the metrics clearly
  map to the domain in the requirement.

**2B) Board-Approved Equivalence:**
RCC / Audit Committee / Executive Committee / Security Committee with board authority all count.
Document control block with Approving Authority + Approval Date + Version = sufficient approval proof.

**2C) Digital = Physical:**
Jira/ServiceNow approvals with status/approver/date = signed forms. DocuSign/Signit = physical signature.
ITSM tickets showing change records, risk acceptances, security reviews with approval status ARE formal
records, not "informal screenshots." Specifically: a Jira/ITSM screenshot showing a change request with
security validation steps, acceptance criteria, or security review sections IS a "change management record
showing security review" — score as DIRECT_MATCH

**2D) Combined Governance:**
A "Risk & Compliance Committee Charter" with explicit cybersecurity mandate satisfies "Cyber Security
Committee Charter."

**2E) Multi-File Packages — CRITICAL for "list" requirements:**
Multiple files = evaluate COLLECTIVELY as one package. First catalog what each file shows, then count
distinct categories across ALL files:
- 8 files showing 5+ different monitoring tools → DIRECT_MATCH, evidence_strength 80+
- 2 files from one narrow area → PARTIAL_MATCH, evidence_strength ≤ 40
The files themselves ARE the list. Do not require a separate "list document."
- **Domain relevance in packages:** when the requirement is domain-specific (e.g., Physical Security,
  Third-Party, HR), only count files that address that domain. A cyber/technical security document
  (vulnerability scans, code KPIs) does NOT contribute to a Physical Security evaluation requirement
  even when included in the same package — assess it as non-contributing and score on the files that
  actually match the domain.

**2F) Maturity Level:**
At L1-L2: drafts, ad-hoc evidence, process docs with KPIs can satisfy "review report" requirements.
At L3+: formal approval expected; process docs for register requirements = TYPE_MISMATCH.

# STEP 3 — Intent Alignment (after applying Step 2 equivalences)

Compare the two questions from Step 1 and classify:

**Intent Alignment:**
- SAME_QUESTION = evidence directly answers the requirement
- RELATED_QUESTION = partial overlap or close but not exact
- DIFFERENT_QUESTION = no meaningful overlap

**Semantic Match:**
- DIRECT_MATCH = SAME_QUESTION + functionally satisfies requirement (including via Step 2 equivalences)
- PARTIAL_MATCH = RELATED_QUESTION or missing key elements
- TYPE_MISMATCH = about the topic but wrong deliverable AND not covered by any Step 2 equivalence
- DOMAIN_MISMATCH = different security domain (file references different SAMA CSF control)
- UNRELATED = different topic entirely

**Hard caps on evidence_strength (0-100):**
- DIRECT_MATCH and complete → 85-100
- PARTIAL_MATCH → 40-80
- TYPE_MISMATCH → 15-40
- DOMAIN_MISMATCH or DIFFERENT_QUESTION → 10-15
- UNRELATED → 0

# STEP 4 — Self-Check Before Locking Classification

Before finalizing the semantic_match label:
1. If TYPE_MISMATCH: re-read Step 2A-2F and verify NO equivalence applies.
2. If DOMAIN_MISMATCH: verify the evidence is truly for a different control.
3. If multiple files and not DIRECT_MATCH: re-read Step 2E and count distinct categories.
4. If requirement uses a governance term (Charter, Policy, Procedure, Register, Acceptance, Appetite):
   re-read Key Concept Disambiguations.

Only after this self-check can the hard cap from Step 3 be applied.

# STEP 5 — Build 5 Micro-Requirements (MR1..MR5)
Derive from the requirement intent. Each must be audit-checkable.
At least one must be intent-defining (cannot be satisfied by wrong deliverable type).

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
```

---

## 9. User Message Template

At call time, `_build_user_message()` prepends this context block before the document content:

```
## Context
- **Framework:** 'Cyber Security Framework (CSF)'
- **Issuing Authority:** 'Saudi Arabian Monetary Authority (SAMA)'
- **Domain:** '<domain name>'
- **Subdomain:** '<subdomain name>'
- **Control:** '<control_code> - <control_title>'
- **Control Description:** '<control description>'
- **Guideline:** 'N/A'
- **Maturity Level:** '<L1|L2|L3>'
- **Evidence Inventory:** '<file1>; <file2>; ...'

## Evidence Under Evaluation
- **Requirement Code:** '<evidence_code>'
- **Requirement:** '<requirement description>'
- **Files (<N> total):** '<file1>; <file2>; ...'

## Document Content

--- Document 1: <filename> ---
<full document text>

--- Document 2: <filename> ---
<full document text>
...
```

---

## 10. Technical Notes

### Thinking mode
Thinking mode was tested ON and OFF during development. **Thinking OFF** was selected for all final benchmark runs because:
- Thinking ON made TC4 drop below threshold (60% → 55%)
- Thinking ON caused TC6 failure score to increase (45% → 60%)
- Thinking OFF is faster and produces cleaner JSON output

For Qwen3 models, thinking is disabled via `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`.

### JSON extraction
Without `--reasoning-parser qwen3`, the vLLM server outputs thinking as raw text ending with `</think>` (no opening tag). The `_extract_json()` function handles this via:
```python
if "</think>" in raw:
    raw = raw[raw.rindex("</think>") + len("</think>"):].strip()
```
`json_repair` is used as a fallback for malformed JSON (e.g. unescaped quotes in Arabic text).

### AWQ models
AWQ models use `compressed-tensors` internally in vLLM 0.22.1. Do **not** pass `--quantization awq` — it causes a load error.

### MoE model context limits
- `Qwen3-30B-A3B-FP8`: native max context 40960 — use `--max-model-len 32768`
- `Gemma4-26B-A4B`: native max context ~32768-40960 — use `--max-model-len 32768`
- TC6 has ~24,577–28,673 input tokens; with 32768-token context, `max_tokens` must be ≤ 2048

### Stale EngineCore processes
After `pkill -f vllm`, the `VLLM::EngineCore` child process may hold GPU VRAM. Fix:
```bash
nvidia-smi --query-compute-apps=pid,used_memory,name --format=csv,noheader
kill <engine_core_pid>
```
