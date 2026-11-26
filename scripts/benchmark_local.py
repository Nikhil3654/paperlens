"""Benchmark the *current, in-memory* PaperLens service without an HTTP server.

Suitable for Kaggle notebooks. Metrics are computed from live model predictions,
not taken from the README or a constant in the API.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from scripts.benchmark_api import score_response, summarise, write_markdown


def run_benchmark(service, questions_file="data/questions/paperlens_questions.csv",
                  output_dir="reports/retrieval_benchmark", max_questions=None):
    if not service.ready():
        raise RuntimeError("Build the PaperLens index before running the benchmark.")
    question_path = Path(questions_file)
    with question_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        questions = [r for r in reader if r.get("question", "").strip()]
    if max_questions is not None:
        questions = questions[:max_questions]
    if not questions:
        raise ValueError("Question CSV must contain at least one question.")

    results = []
    modes = ("semantic", "hybrid")
    for mode in modes:
        for i, question in enumerate(questions, start=1):
            row = {"mode": mode, "question": question["question"],
                   "expected_paper": question.get("expected_paper", ""),
                   "expected_pages": question.get("expected_pages", "")}
            try:
                start = time.perf_counter()
                response = service.search(question["question"], search_mode=mode)
                row["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
                row.update(score_response(question, response))
            except Exception as error:
                row["error"] = f"{type(error).__name__}: {error}"
            results.append(row)
            print(f"[{mode} {i}/{len(questions)}] " + ("FAILED" if row.get("error") else "done"))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cols = list(dict.fromkeys(key for r in results for key in r))
    with (output_dir / "details.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols)
        writer.writeheader()
        writer.writerows(results)
    summary = summarise(results, list(modes))
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary, output_dir / "comparison.md")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", default="data/questions/paperlens_questions.csv")
    parser.add_argument("--output", default="reports/retrieval_benchmark")
    parser.add_argument("--max-questions", type=int, default=None)
    args = parser.parse_args()

    from api.paper_service import PaperLensService
    service = PaperLensService()
    service.build_sample_index()
    report = run_benchmark(service, args.questions, args.output, args.max_questions)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
