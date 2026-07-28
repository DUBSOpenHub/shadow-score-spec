#!/usr/bin/env python3
"""
Shadow Score Reference Validator

Computes Shadow Score from test result files (JSON format).
Conforms to Shadow Score Spec v2.0.0.

Usage:
    python shadow-score.py --sealed sealed-results.json --open open-results.json
    python shadow-score.py --sealed sealed-results.json
    python shadow-score.py --sealed sealed-results.json --threshold 15

Input format (sealed-results.json):
{
  "tests": [
    {"name": "test_name", "status": "passed|failed", "category": "happy_path|edge_case|error_handling|security"},
    {"name": "test_name", "status": "failed", "expected": "...", "actual": "...", "message": "..."}
  ]
}
"""

import argparse
import json
import sys
from pathlib import Path

SPEC_VERSION = "2.0.0"

CATEGORIES = ["happy_path", "edge_case", "error_handling", "security"]

LEVELS = [
    (0, "perfect", "✅"),
    (15, "minor", "🟢"),
    (30, "moderate", "🟡"),
    (50, "significant", "🟠"),
    (100, "critical", "🔴"),
]


def classify_gap(score: float) -> tuple[str, str]:
    for threshold, level, indicator in LEVELS:
        if score <= threshold:
            return level, indicator
    return "critical", "🔴"


def load_results(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data.get("tests", [])


def compute_shadow_score(sealed: list[dict]) -> dict:
    total = len(sealed)
    if total == 0:
        return {"shadow_score": 0.0, "level": "perfect", "indicator": "✅",
                "total": 0, "passed": 0, "failed": 0, "failures": []}

    failures = [t for t in sealed if t.get("status") == "failed"]
    passed = total - len(failures)
    score = (len(failures) / total) * 100
    level, indicator = classify_gap(score)

    return {
        "shadow_score": round(score, 1),
        "level": level,
        "indicator": indicator,
        "total": total,
        "passed": passed,
        "failed": len(failures),
        "failures": failures,
    }


def build_coverage_comparison(sealed: list[dict], open_tests: list[dict]) -> dict:
    comparison = {}
    for cat in CATEGORIES:
        s_count = sum(1 for t in sealed if t.get("category") == cat)
        o_count = sum(1 for t in open_tests if t.get("category") == cat)
        comparison[cat] = {"sealed": s_count, "open": o_count, "delta": s_count - o_count}
    return comparison


def build_report(sealed: list[dict], open_tests: list[dict] | None = None) -> dict:
    result = compute_shadow_score(sealed)

    report = {
        "shadow_score_spec_version": SPEC_VERSION,
        "report": {
            "shadow_score": result["shadow_score"],
            "level": result["level"],
        },
        "sealed_tests": {
            "total": result["total"],
            "passed": result["passed"],
            "failed": result["failed"],
        },
        "failures": [
            {
                "test_name": f.get("name", "unknown"),
                "category": f.get("category", "unknown"),
                "expected": f.get("expected", ""),
                "actual": f.get("actual", ""),
                "message": f.get("message", ""),
            }
            for f in result["failures"]
        ],
    }

    if open_tests is not None:
        o_total = len(open_tests)
        o_failed = sum(1 for t in open_tests if t.get("status") == "failed")
        report["open_tests"] = {
            "total": o_total,
            "passed": o_total - o_failed,
            "failed": o_failed,
        }
        report["coverage_comparison"] = build_coverage_comparison(sealed, open_tests)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Shadow Score Reference Validator (Spec v2.0.0)"
    )
    parser.add_argument("--sealed", required=True, help="Path to sealed test results JSON")
    parser.add_argument("--open", help="Path to open test results JSON (optional)")
    parser.add_argument("--threshold", type=float, default=None,
                        help="Exit with code 1 if Shadow Score exceeds this threshold")
    parser.add_argument("--format", choices=["json", "summary"], default="json",
                        help="Output format (default: json)")
    args = parser.parse_args()

    sealed = load_results(args.sealed)
    open_tests = load_results(args.open) if args.open else None

    report = build_report(sealed, open_tests)

    if args.format == "summary":
        r = report
        score = r["report"]["shadow_score"]
        level = r["report"]["level"]
        _, indicator = classify_gap(score)
        print(f"Shadow Score: {score}% {indicator} ({level})")
        print(f"Sealed: {r['sealed_tests']['passed']}/{r['sealed_tests']['total']} passed")
        if "open_tests" in r:
            print(f"Open:   {r['open_tests']['passed']}/{r['open_tests']['total']} passed")
        if r["failures"]:
            print(f"\nFailures ({len(r['failures'])}):")
            for f in r["failures"]:
                print(f"  ❌ {f['test_name']}: {f['message']}")
    else:
        print(json.dumps(report, indent=2))

    if args.threshold is not None and report["report"]["shadow_score"] > args.threshold:
        sys.exit(1)


if __name__ == "__main__":
    main()
