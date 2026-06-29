#!/usr/bin/env python3
"""
Benchmark v2 — uses compliance_scorer_v2.py (new prompt).

Saves results to benchmark_results_v2_<model>.json so they can be
compared side-by-side with the v1 results (benchmark_results_<model>.json).

Usage:
    VLLM_BASE_URL=http://localhost:8000/v1 VLLM_MODEL=<model> python3 benchmark_v2.py

Compare v1 vs v2 for a given model:
    python3 compare_prompts.py <model>
"""

import os
import re
import json
import time
from pathlib import Path
from compliance_scorer_v2 import score_documents, PROMPT_VERSION

import pypdfium2

BASE_DIR = Path(__file__).parent

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


def _read_pdf(path: Path) -> tuple[str, list[str] | None]:
    pdf = pypdfium2.PdfDocument(str(path))
    pages = []
    for page in pdf:
        textpage = page.get_textpage()
        pages.append(textpage.get_text_range())
        textpage.close()
        page.close()
    pdf.close()
    text = "\n\n".join(pages).strip()
    return text, None


def _read_text(path: Path) -> tuple[str, list[str] | None]:
    raw = path.read_text(encoding="utf-8")
    image_tags = re.findall(r"<!--\s*image\s*-->", raw, flags=re.IGNORECASE)
    doc_extra = [f"{len(image_tags)} image placeholder(s)"] if image_tags else None
    doc_text = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL).strip()
    return doc_text, doc_extra


TEST_CASES = [
    "SAMA-3.1.1-5-L3-1",
    "SAMA-3.1.1-5-L3-2",
    "SAMA-3.1.3-2-L3-1",
    "SAMA-3.2.1.3-3-L3-1",
    "SAMA-3.2.4-2-L3-2",
    "SAMA-3.3.2-2-L3-1",
]


def load_docs(folder: Path) -> list[dict]:
    files = [f for f in sorted(folder.iterdir()) if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]
    md_stems = {f.stem for f in files if f.suffix.lower() == ".md"}
    docs = []
    for f in files:
        if f.suffix.lower() == ".pdf" and f.stem in md_stems:
            continue
        if f.suffix.lower() == ".pdf":
            doc_text, doc_extra = _read_pdf(f)
        else:
            doc_text, doc_extra = _read_text(f)
        if not doc_text:
            print(f"  WARNING: {f.name} produced no text — skipping")
            continue
        docs.append({"doc_name": f.name, "doc_text": doc_text, "doc_extra": doc_extra})
    return docs


def score_set(evidence_code: str, folder: Path, label: str) -> dict:
    docs = load_docs(folder)
    if not docs:
        return {"score_percentage": 0.0, "present": False, "reasoning": "No documents found.", "doc_names": []}
    print(f"  [{label}] scoring {len(docs)} doc(s): {[d['doc_name'] for d in docs]}")
    result = score_documents(evidence_code=evidence_code, documents=docs)
    return result


def main():
    model = os.environ.get("VLLM_MODEL", "unknown")
    results = []

    for tc in TEST_CASES:
        tc_dir = BASE_DIR / tc
        print(f"\n{'='*60}")
        print(f"Test case: {tc}")

        t0 = time.time()
        success_result = score_set(tc, tc_dir / "Success", "Success")
        failure_result = score_set(tc, tc_dir / "Failure", "Failure")
        elapsed = time.time() - t0

        def _mr_summary(result: dict) -> str:
            mrs = result.get("micro_requirements", [])
            if not mrs:
                return ""
            return " | ".join(f"{m['id']}={m['met_score']}" for m in mrs)

        results.append({
            "test_case": tc,
            "prompt_version": PROMPT_VERSION,
            "success_score": success_result["score_percentage"],
            "success_present": success_result["present"],
            "success_reasoning": success_result.get("explanation_en", success_result.get("reasoning", "")),
            "success_semantic_match": success_result.get("semantic_analysis", {}).get("semantic_match", ""),
            "success_reliability": success_result.get("reliability", ""),
            "success_micro_summary": _mr_summary(success_result),
            "success_actions": success_result.get("actions_needed_en", []),
            "failure_score": failure_result["score_percentage"],
            "failure_present": failure_result["present"],
            "failure_reasoning": failure_result.get("explanation_en", failure_result.get("reasoning", "")),
            "failure_semantic_match": failure_result.get("semantic_analysis", {}).get("semantic_match", ""),
            "failure_reliability": failure_result.get("reliability", ""),
            "failure_micro_summary": _mr_summary(failure_result),
            "failure_actions": failure_result.get("actions_needed_en", []),
            "elapsed_seconds": round(elapsed, 1),
            "success_full": success_result,
            "failure_full": failure_result,
        })

    # ── Summary table ──────────────────────────────────────────────────────────
    print(f"\n\n{'='*60}")
    print(f"BENCHMARK RESULTS — Prompt {PROMPT_VERSION}")
    print(f"{'='*60}")

    col_tc = 26
    col_sc = 16
    col_fl = 16
    col_ok = 8
    col_t  = 10

    header = (
        f"{'Test Case':<{col_tc}}"
        f"{'Success Score':>{col_sc}}"
        f"{'  Present':<{col_ok}}"
        f"{'Failure Score':>{col_fl}}"
        f"{'  Present':<{col_ok}}"
        f"{'Time':>{col_t}}"
    )
    print(header)
    print("-" * (col_tc + col_sc + col_ok + col_fl + col_ok + col_t))

    for r in results:
        line = (
            f"{r['test_case']:<{col_tc}}"
            f"{r['success_score']:>{col_sc}.1f}%"
            f"  {'YES' if r['success_present'] else 'NO':<{col_ok - 2}}"
            f"{r['failure_score']:>{col_fl}.1f}%"
            f"  {'YES' if r['failure_present'] else 'NO':<{col_ok - 2}}"
            f"{r['elapsed_seconds']:>{col_t}.1f}s"
        )
        print(line)

    print(f"{'='*60}")

    # ── Reasoning detail ───────────────────────────────────────────────────────
    print("\nREASONING DETAIL")
    print(f"{'='*60}")
    for r in results:
        print(f"\n{r['test_case']}")
        for label in ("success", "failure"):
            score = r[f"{label}_score"]
            match = r.get(f"{label}_semantic_match", "")
            reliability = r.get(f"{label}_reliability", "")
            reasoning = r[f"{label}_reasoning"]
            mr_summary = r.get(f"{label}_micro_summary", "")
            print(f"  [{label.upper()}] score={score:.0f}  match={match}  reliability={reliability}")
            print(f"    {reasoning}")
            if mr_summary:
                print(f"    MR scores: {mr_summary}")
            actions = r.get(f"{label}_actions", [])
            if actions:
                for a in actions[:3]:
                    print(f"    • {a}")

    # ── JSON dump ─────────────────────────────────────────────────────────────
    safe_model = model.replace("/", "_").replace(":", "_")
    out_path = BASE_DIR / f"benchmark_results_v2_{safe_model}.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nFull results saved to {out_path}")

    # ── Quick diff vs v1 ──────────────────────────────────────────────────────
    v1_path = BASE_DIR / f"benchmark_results_{safe_model}.json"
    if v1_path.exists():
        v1 = {r["test_case"]: r for r in json.loads(v1_path.read_text())}
        print(f"\n{'='*60}")
        print(f"DIFF vs v1 (prompt v1 → v2)")
        print(f"{'='*60}")
        print(f"{'Test Case':<26}  {'v1 S/F':>12}  {'v2 S/F':>12}  {'Δ Success':>10}  {'Δ Failure':>10}  Result")
        print("-" * 80)
        v1_pass = v2_pass = 0
        for r in results:
            tc = r["test_case"]
            r1 = v1.get(tc)
            if not r1:
                continue
            ds = r["success_score"] - r1["success_score"]
            df = r["failure_score"] - r1["failure_score"]
            v1_ok = "✅" if (r1["success_present"] and not r1["failure_present"]) else "❌"
            v2_ok = "✅" if (r["success_present"] and not r["failure_present"]) else "❌"
            if r1["success_present"] and not r1["failure_present"]: v1_pass += 1
            if r["success_present"] and not r["failure_present"]: v2_pass += 1
            ds_str = f"{ds:+.0f}%"
            df_str = f"{df:+.0f}%"
            v1_str = f"{r1['success_score']:.0f}%/{r1['failure_score']:.0f}%"
            v2_str = f"{r['success_score']:.0f}%/{r['failure_score']:.0f}%"
            print(f"{tc:<26}  {v1_str:>12}  {v2_str:>12}  {ds_str:>10}  {df_str:>10}  {v1_ok}→{v2_ok}")
        print("-" * 80)
        print(f"{'PASS COUNT':<26}  {v1_pass}/6{'':<10}  {v2_pass}/6")
    else:
        print(f"\n(No v1 results found at {v1_path} — run benchmark.py first to enable diff)")


if __name__ == "__main__":
    main()
