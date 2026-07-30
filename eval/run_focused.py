"""Focused eval runner — runs a subset of test cases by ID.

Usage:
    python eval/run_focused.py                          # re-run last failing cases
    python eval/run_focused.py hybrid-01 hybrid-03      # specific IDs
    python eval/run_focused.py --category hybrid        # all cases in a category
    python eval/run_focused.py --failing                # auto-detect from latest results
    python eval/run_focused.py --all                    # all cases (same as run_eval.py)
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents import run_agent, setup_logging
from app.tools import database
from eval.run_eval import CASES_PATH, RESULTS_DIR, evaluate_case

logger = logging.getLogger(__name__)


def _failing_ids_from_latest_results() -> list[str]:
    """Return IDs of cases that failed any check in the most recent eval run."""
    if not RESULTS_DIR.exists():
        return []
    result_files = sorted(RESULTS_DIR.glob("eval_*.json"))
    if not result_files:
        return []
    latest = json.loads(result_files[-1].read_text())
    failing = []
    for r in latest["results"]:
        checks = [r["intent_ok"], r["keyword_ok"]]
        if r["query_ok"] is not None:
            checks.append(r["query_ok"])
        if r["sources_ok"] is not None:
            checks.append(r["sources_ok"])
        if r["tool_ok"] is not None:
            checks.append(r["tool_ok"])
        if not all(checks) or r["error"]:
            failing.append(r["id"])
    return failing


def main() -> None:
    setup_logging(logging.WARNING)

    args = sys.argv[1:]
    all_cases = json.loads(CASES_PATH.read_text())

    if "--all" in args:
        target_ids = [c["id"] for c in all_cases]
    elif "--category" in args:
        idx = args.index("--category")
        category = args[idx + 1]
        target_ids = [c["id"] for c in all_cases if c["category"] == category]
    elif "--failing" in args:
        target_ids = _failing_ids_from_latest_results()
        if not target_ids:
            print("No failing cases found in latest results (or no results yet).")
            sys.exit(0)
    elif args:
        target_ids = [a for a in args if not a.startswith("--")]
    else:
        # Default: auto-detect failures from the latest run, or run all if no results.
        target_ids = _failing_ids_from_latest_results() or [c["id"] for c in all_cases]

    cases = [c for c in all_cases if c["id"] in target_ids]
    if not cases:
        print(f"No cases matched: {target_ids}")
        sys.exit(1)

    print(f"Running {len(cases)} case(s): {[c['id'] for c in cases]}\n")
    database.reset_seed_data()

    for case in cases:
        result = evaluate_case(case)
        intent_mark = "✓" if result["intent_ok"] else "✗"
        keyword_mark = "✓" if result["keyword_ok"] else "✗"
        print(f"[{result['id']}] intent {intent_mark}  keywords {keyword_mark}  ({result['latency_seconds']:.1f}s)")
        print(f"  Q: {result['input']}")
        print(f"  A: {result['reply'][:400]}")
        if result.get("error"):
            print(f"  ERROR: {result['error']}")
        missing = [
            kw for kw in case.get("expected_keywords", [])
            if kw.lower() not in result["reply"].lower()
        ]
        if missing:
            print(f"  Missing keywords: {missing}")
        print()
        time.sleep(1)


if __name__ == "__main__":
    main()
