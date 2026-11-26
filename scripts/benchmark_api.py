"""Compare PaperLens API retrieval modes against a labeled question CSV.

Run from the PaperLens project root, with PaperLens running locally:
    python scripts/benchmark_api.py --questions data/questions/<your-file>.csv

This script uses Python's standard library only. It does not create or change
search indexes or make claims about LLM answer faithfulness.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def parse_pages(raw: object) -> set[int]:
    """Interpret comma-separated page labels, ignoring empty values."""
    value = str(raw or "").strip()
    if not value:
        return set()
    return {int(part.strip()) for part in value.split(",") if part.strip()}


def parse_bool(raw: object) -> bool | None:
    value = str(raw or "").lower().strip()
    if value in {"1", "true", "yes", "y"}:
        return True
    if value in {"0", "false", "no", "n"}:
        return False
    return None


def safe_evidence(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Support the current PaperLens `evidence_used` response shape."""
    evidence = response.get("evidence_used", response.get("evidence", []))
    return [item for item in evidence if isinstance(item, dict)] if isinstance(evidence, list) else []


def score_response(question: dict[str, str], response: dict[str, Any]) -> dict[str, Any]:
    """Score answerable retrieval separately from negative-question abstention.

    The citation check tests only that cited IDs occur in returned evidence;
    it does NOT test whether an answer statement is actually supported.
    """
    expected_paper = question.get("expected_paper", "").strip()
    pages = parse_pages(question.get("expected_pages", ""))
    evidence = safe_evidence(response)
    answerable = parse_bool(question.get("answerable", ""))

    # Negative questions have no expected relevant paper. Counting the first
    # retrieved paper as a miss would make paper accuracy meaningless.
    if answerable is False:
        top1 = top5 = strict_page_hit = reciprocal_rank = None
    else:
        top1 = bool(evidence and evidence[0].get("paper_title") == expected_paper)
        top5 = any(e.get("paper_title") == expected_paper for e in evidence[:5])
        strict_page_hit = (
            any(
                e.get("paper_title") == expected_paper
                and int(e.get("page_number", -1)) in pages
                for e in evidence[:5]
            )
            if pages else None
        )
        rank = next((i for i, e in enumerate(evidence[:5], 1)
                     if e.get("paper_title") == expected_paper), None)
        reciprocal_rank = 1 / rank if rank else 0.0

    evidence_ids = {
        (e.get("paper_title"), str(e.get("page_number")), e.get("chunk_id"))
        for e in evidence
    }
    citations = response.get("citations")
    if isinstance(citations, list):
        valid_citations = (
            all(
                isinstance(c, dict)
                and (c.get("paper_title"), str(c.get("page_number")), c.get("chunk_id"))
                in evidence_ids
                for c in citations
            ) if citations else None
        )
    else:
        valid_citations = False

    # Not calibrated yet; only records an explicit refusal without citations.
    abstained = response.get("confidence") == "low" and not citations
    return {
        "top1_paper_hit": top1,
        "top5_paper_hit": top5,
        "strict_paper_page_hit_at5": strict_page_hit,
        "reciprocal_rank_at5": reciprocal_rank,
        "citation_mapping_valid": valid_citations,
        "citation_count": len(citations) if isinstance(citations, list) else None,
        "answerable": answerable,
        "correct_abstention": abstained if answerable is False else None,
        "false_abstention": abstained if answerable is True else None,
        "evidence_count": len(evidence),
    }


def call_search(url: str, question: str, mode: str, timeout: float) -> tuple[dict[str, Any], float]:
    body = json.dumps({"question": question, "search_mode": mode}).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    with urlopen(request, timeout=timeout) as result:
        data = json.load(result)
    elapsed_ms = (time.perf_counter() - started) * 1000
    if not isinstance(data, dict):
        raise ValueError("API response is not an object")
    return data, elapsed_ms


def mean_of(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(r[key]) for r in rows if r.get(key) is not None and not r.get("error")]
    return statistics.mean(values) if values else None


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    pos = (len(s) - 1) * p
    i = math.floor(pos)
    return s[i] + (s[min(i + 1, len(s) - 1)] - s[i]) * (pos - i)


def summarise(rows: list[dict[str, Any]], modes: list[str]) -> dict[str, dict[str, Any]]:
    out = {}
    for mode in modes:
        relevant = [r for r in rows if r["mode"] == mode]
        completed = [r for r in relevant if not r.get("error")]
        latencies = [r["latency_ms"] for r in completed]
        out[mode] = {
            "total_queries": len(relevant),
            "successful_queries": len(completed),
            "failed_queries": len(relevant) - len(completed),
            "top1_paper_accuracy": mean_of(completed, "top1_paper_hit"),
            "top5_paper_recall": mean_of(completed, "top5_paper_hit"),
            "strict_paper_page_hit_at5": mean_of(completed, "strict_paper_page_hit_at5"),
            "mrr_at5": mean_of(completed, "reciprocal_rank_at5"),
            "citation_mapping_valid_rate": mean_of(completed, "citation_mapping_valid"),
            "negative_question_abstention": mean_of(completed, "correct_abstention"),
            "positive_question_false_abstention": mean_of(completed, "false_abstention"),
            "latency_p50_ms": percentile(latencies, 0.5),
            "latency_p95_ms": percentile(latencies, 0.95),
        }
    return out


def load_questions(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"question", "expected_paper"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV needs columns: {', '.join(sorted(required))}")
        questions = [r for r in reader if r["question"].strip()]
    if not questions:
        raise ValueError("Question dataset is empty")
    return questions


def fmt(value: Any) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def write_markdown(summary: dict[str, dict[str, Any]], path: Path) -> None:
    headings = [
        ("top1_paper_accuracy", "Top-1 paper accuracy"),
        ("top5_paper_recall", "Top-5 paper recall"),
        ("strict_paper_page_hit_at5", "Strict paper + page hit@5"),
        ("mrr_at5", "MRR@5"),
        ("citation_mapping_valid_rate", "Citation mapping validity"),
        ("negative_question_abstention", "Negative-question abstention"),
        ("positive_question_false_abstention", "False abstention on answerable queries"),
        ("latency_p50_ms", "P50 latency (ms)"),
        ("latency_p95_ms", "P95 latency (ms)"),
    ]
    modes = list(summary)
    lines = ["# PaperLens retrieval benchmark", "",
             "Scores reflect the supplied labeled dataset and API responses, not a claim of general performance.", "",
             "| Metric | " + " | ".join(modes) + " |",
             "|---|" + "---:|" * len(modes)]
    for key, label in headings:
        lines.append("| " + label + " | " + " | ".join(fmt(summary[m][key]) for m in modes) + " |")
    lines += ["", "Results with unavailable labels are shown as n/a.",
              "If requests failed, results only summarize successful requests; inspect details.csv.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True, type=Path, help="CSV with question, expected_paper, expected_pages")
    parser.add_argument("--base-url", default="http://127.0.0.1:7860")
    parser.add_argument("--output", type=Path, default=Path("reports/retrieval_benchmark"))
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--modes", nargs="+", choices=("semantic", "hybrid"), default=["semantic", "hybrid"])
    args = parser.parse_args()
    questions = load_questions(args.questions)
    rows: list[dict[str, Any]] = []
    endpoint = args.base_url.rstrip("/") + "/api/search"
    for mode in args.modes:
        for index, q in enumerate(questions, 1):
            row: dict[str, Any] = {"mode": mode, "question": q["question"],
                                   "expected_paper": q["expected_paper"],
                                   "expected_pages": q.get("expected_pages", "")}
            try:
                response, elapsed_ms = call_search(endpoint, q["question"], mode, args.timeout)
                row.update(score_response(q, response))
                row["latency_ms"] = round(elapsed_ms, 2)
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError) as exc:
                row["error"] = str(exc)
            rows.append(row)
            print(f"[{mode} {index}/{len(questions)}] {q['question'][:60]} {'ERROR' if row.get('error') else 'OK'}")
    args.output.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (args.output / "details.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = summarise(rows, args.modes)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary, args.output / "comparison.md")
    print(f"\nSaved results to {args.output}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
