"""Reproducible read-only audit of Kaggle's PaperLens_Benchmark_Results.zip.

Creates a per-question comparison matrix and a plain-language audit report.
Does not rerun the model or imply that a new model was trained.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
from zipfile import ZipFile


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n))/d
    r = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return c-r, c+r


def audit(zip_path: Path, output_dir: Path, readme_path: Path | None = None) -> dict:
    with ZipFile(zip_path) as z:
        details = list(csv.DictReader(io.StringIO(z.read('details.csv').decode('utf-8-sig'))))
        old_summary = json.loads(z.read('summary.json'))
    if not details:
        raise ValueError('details.csv has no rows')
    by_q: dict[str, dict[str, dict]] = defaultdict(dict)
    modes = list(dict.fromkeys(r['mode'] for r in details))
    for row in details:
        question = row['question']
        mode = row['mode']
        if mode in by_q[question]:
            raise ValueError(f'duplicate mode/question: {mode}/{question}')
        by_q[question][mode] = row
    matrix = []
    for question, mode_rows in by_q.items():
        row = {'question': question}
        for mode in modes:
            r = mode_rows.get(mode)
            row[f'{mode}_status'] = ('ERROR' if r.get('error') else
                                     'HIT' if r.get('strict_paper_page_hit_at5') == 'True' else
                                     'MISS') if r else 'MISSING'
            row[f'{mode}_latency_ms'] = r.get('latency_ms', '') if r else ''
        matrix.append(row)
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = list(dict.fromkeys(k for r in matrix for k in r))
    with (output_dir / 'question_comparison.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(matrix)
    overlap = []
    if readme_path and readme_path.is_file():
        readme = readme_path.read_text(encoding='utf-8')
        overlap = [q for q in by_q if q in readme]
    per_mode = {}
    for mode in modes:
        rows = [r for r in details if r['mode'] == mode]
        successful = [r for r in rows if not r.get('error')]
        measured = [r for r in successful if r.get('strict_paper_page_hit_at5') in {'True','False'}]
        k = sum(r['strict_paper_page_hit_at5'] == 'True' for r in measured)
        n = len(measured)
        lat = [float(r['latency_ms']) for r in successful if r.get('latency_ms')]
        per_mode[mode] = {
            'n_queries': len(rows), 'n_completed': len(successful),
            'strict_hits': k, 'strict_labeled': n,
            'strict_hit_rate': k/n if n else None,
            'wilson_95_pct': tuple(round(x*100, 1) for x in wilson(k, n)) if n else None,
            'median_latency_ms': median(lat) if lat else None,
            'missed_queries': [r['question'] for r in measured if r['strict_paper_page_hit_at5'] == 'False'],
            'negative_questions': sum(r.get('answerable') == 'False' for r in rows),
        }
    report = {'per_mode': per_mode, 'readme_demo_overlap_count': len(overlap),
              'readme_demo_overlap_queries': overlap,
              'question_count': len(by_q),
              'reported_summary': old_summary}
    (output_dir / 'audited_summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    lines = ['# Independent audit of submitted PaperLens benchmark', '',
             '> Read-only recomputation from the uploaded CSV; this is not a fresh model run.', '']
    for mode, m in per_mode.items():
        lines += [f'## {mode}', '',
                  f'- Expected paper/page match: {m["strict_hits"]}/{m["strict_labeled"]} '
                  f'({m["strict_hit_rate"]:.1%}); Wilson 95% interval {m["wilson_95_pct"]}%',
                  f'- Successful requests: {m["n_completed"]}/{m["n_queries"]}',
                  f'- Median latency: {m["median_latency_ms"]:.2f}ms',
                  f'- Labeled negative questions: {m["negative_questions"]}',
                  '- Missed annotated questions: ' + ('; '.join(m['missed_queries']) or 'None'), '']
    lines += [f'Readme demo overlap: {len(overlap)} of {len(by_q)} questions. '
              'These are smoke tests, not an independent held-out evaluation.', '',
              '## Interpretation', '',
              '- Correct-paper scores do not measure whether the answer is supported by relevant evidence.',
              '- Citation ID mapping is not equivalent to sentence-level citation faithfulness.',
              '- Do not compare semantic and hybrid latency without randomized order, warm-up, and repeated runs.',
              '- Label every negative, multi-paper, and evidence-span example before reporting general performance.', '']
    (output_dir / 'audit.md').write_text('\n'.join(lines), encoding='utf-8')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip_path', type=Path)
    parser.add_argument('--output', type=Path, default=Path('reports/v2_baseline_audit'))
    parser.add_argument('--readme', type=Path, default=Path('README.md'))
    args = parser.parse_args()
    report = audit(args.zip_path, args.output, args.readme)
    print(json.dumps({'modes': report['per_mode'], 'readme_demo_overlap_count': report['readme_demo_overlap_count']}, indent=2))


if __name__ == '__main__':
    main()
