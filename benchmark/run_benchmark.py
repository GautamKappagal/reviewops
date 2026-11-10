#!/usr/bin/env python3
"""Eval gate: measure how well the reviewer catches seeded bugs.

  python benchmark/run_benchmark.py                          # in-process (CI)
  python benchmark/run_benchmark.py --url http://host:8000   # against a running service (canary)

Exit code 1 if recall is too low or the false-positive rate is too high.
Uses only the standard library so Jenkins can run it without installing anything.
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "app"))  # lets this run from a plain checkout


def review_in_process(diff: str) -> dict:
    from reviewops.config import get_settings
    from reviewops.llm import get_llm
    from reviewops.reviewer import run_review
    settings = get_settings()
    return run_review({"diff": diff, "repo": "benchmark/case"}, get_llm(settings), settings)


def review_over_http(base_url: str, diff: str) -> dict:
    req = urllib.request.Request(
        base_url.rstrip("/") + "/review",
        data=json.dumps({"repo": "benchmark/case", "diff": diff}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", default=str(HERE / "cases"))
    parser.add_argument("--url", help="score a running service instead of the in-process reviewer")
    parser.add_argument("--min-recall", type=float, default=float(os.getenv("MIN_RECALL", "0.8")))
    parser.add_argument("--max-fp", type=float, default=float(os.getenv("MAX_FALSE_POSITIVE_RATE", "0.2")))
    args = parser.parse_args()

    cases = Path(args.cases)
    labels = json.loads((cases / "labels.json").read_text())
    caught = missed = false_alarms = clean_ok = 0

    for case_id, label in sorted(labels.items()):
        diff = (cases / f"{case_id}.diff").read_text()
        result = review_over_http(args.url, diff) if args.url else review_in_process(diff)
        flagged = result["verdict"] != "pass"
        if label["bug"]:
            caught, missed = (caught + 1, missed) if flagged else (caught, missed + 1)
        else:
            false_alarms, clean_ok = (false_alarms + 1, clean_ok) if flagged else (false_alarms, clean_ok + 1)
        print(f"  {'OK ' if flagged == label['bug'] else 'BAD'} {case_id}: verdict={result['verdict']}")

    bugs, cleans = caught + missed, false_alarms + clean_ok
    recall = caught / bugs if bugs else 1.0
    fp_rate = false_alarms / cleans if cleans else 0.0
    print(f"recall={recall:.2f} (min {args.min_recall})  false_positive_rate={fp_rate:.2f} (max {args.max_fp})")

    if recall < args.min_recall or fp_rate > args.max_fp:
        print("EVAL GATE: FAILED")
        return 1
    print("EVAL GATE: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
