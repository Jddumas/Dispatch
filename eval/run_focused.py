"""Focused eval runner — runs a subset of test cases by ID.

Usage:
    python eval/run_focused.py                          # default failing cases
    python eval/run_focused.py hybrid-01 hybrid-03      # specific IDs
    python eval/run_focused.py --category hybrid        # all cases in a category
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
from eval.run_eval import CASES_PATH, evaluate_case

logger = logging.getLogger(__name__)

# Cases that were failing / under review — update this list as needed.
DEFAULT_IDS = [
    "hybrid-01",
    "hybrid-02",
    "hybrid-03",
    "hybrid-04",
]


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
    elif args:
        target_ids = args
    else:
        target_ids = DEFAULT_IDS

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
        expected_kw = case.get("expected_keywords", [])
        if expected_kw:
            found = [kw for kw in expected_kw if kw.lower() in result["reply"].lower()]
            missing = [kw for kw in expected_kw if kw.lower() not in result["reply"].lower()]
            if missing:
                print(f"  Missing keywords: {missing}")
        print()
        time.sleep(1)


if __name__ == "__main__":
    main()
