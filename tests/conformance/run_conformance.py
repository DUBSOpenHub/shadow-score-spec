#!/usr/bin/env python3
"""
Conformance Test Runner for Shadow Score Validators

Runs the conformance fixture suite against any validator CLI that accepts
the same interface as the reference Python validator.

Usage:
    python run_conformance.py                              # test Python validator
    python run_conformance.py --validator "go run ../validators/shadow-score.go"
    python run_conformance.py --validator "../validators/shadow-score-go"

The runner checks:
  - JSON output matches expected fields (shadow_score, level, sealed_tests, failures)
  - Exit codes match (0 = under threshold, 1 = over threshold)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

FIXTURES_PATH = os.path.join(os.path.dirname(__file__), "fixtures.json")
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_fixtures():
    with open(FIXTURES_PATH) as f:
        return json.load(f)


def run_validator(validator_cmd, args, cwd=None):
    """Run a validator command and return (exit_code, stdout, stderr)."""
    cmd = validator_cmd.split() + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or REPO_ROOT)
    return result.returncode, result.stdout, result.stderr


def check_output(fixture, actual_output):
    """Compare actual JSON output against expected. Returns list of errors."""
    expected = fixture.get("expected_output")
    if expected is None:
        return []  # threshold-only fixture, no output check

    errors = []
    try:
        actual = json.loads(actual_output)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON output: {e}"]

    # Check required top-level fields
    for key in ["shadow_score_spec_version", "report", "sealed_tests", "failures"]:
        if key not in actual:
            errors.append(f"Missing required key: {key}")

    # Check report values
    if "report" in actual and "report" in expected:
        if actual["report"].get("shadow_score") != expected["report"]["shadow_score"]:
            errors.append(
                f"shadow_score: expected {expected['report']['shadow_score']}, "
                f"got {actual['report'].get('shadow_score')}"
            )
        if actual["report"].get("level") != expected["report"]["level"]:
            errors.append(
                f"level: expected {expected['report']['level']}, "
                f"got {actual['report'].get('level')}"
            )

    # Check sealed_tests counts
    if "sealed_tests" in actual and "sealed_tests" in expected:
        for field in ["total", "passed", "failed"]:
            exp_val = expected["sealed_tests"][field]
            act_val = actual["sealed_tests"].get(field)
            if act_val != exp_val:
                errors.append(f"sealed_tests.{field}: expected {exp_val}, got {act_val}")

    # Check failure count
    if "failures" in actual and "failures" in expected:
        if len(actual["failures"]) != len(expected["failures"]):
            errors.append(
                f"failures count: expected {len(expected['failures'])}, "
                f"got {len(actual['failures'])}"
            )

    # Check coverage_comparison if expected
    if "coverage_comparison" in expected:
        if "coverage_comparison" not in actual:
            errors.append("Missing coverage_comparison (expected when --open provided)")
        else:
            for cat in ["happy_path", "edge_case", "error_handling", "security"]:
                if cat not in actual["coverage_comparison"]:
                    errors.append(f"Missing coverage_comparison.{cat}")

    return errors


def run_fixture(validator_cmd, fixture):
    """Run a single fixture. Returns (passed, errors)."""
    inp = fixture["input"]
    args = []

    # Handle sealed input (file reference or inline)
    if "sealed" in inp:
        args.extend(["--sealed", os.path.join(REPO_ROOT, inp["sealed"])])
    elif "sealed_inline" in inp:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(inp["sealed_inline"], tmp)
        tmp.close()
        args.extend(["--sealed", tmp.name])

    # Handle open input
    if "open" in inp:
        args.extend(["--open", os.path.join(REPO_ROOT, inp["open"])])

    # Handle threshold
    if "threshold" in inp:
        args.extend(["--threshold", str(inp["threshold"])])

    try:
        exit_code, stdout, stderr = run_validator(validator_cmd, args)
    finally:
        # Clean up inline temp files
        if "sealed_inline" in inp:
            os.unlink(tmp.name)

    errors = []

    # Check exit code
    expected_exit = fixture["expected_exit_code"]
    if exit_code != expected_exit:
        errors.append(f"exit code: expected {expected_exit}, got {exit_code}")

    # Check output (only for non-threshold-only fixtures)
    if "expected_output" in fixture:
        errors.extend(check_output(fixture, stdout))

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Shadow Score Conformance Test Runner")
    parser.add_argument(
        "--validator",
        default=f"python3 {os.path.join(REPO_ROOT, 'validators', 'shadow-score.py')}",
        help="Validator command to test (default: Python reference validator)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show details for all fixtures")
    args = parser.parse_args()

    suite = load_fixtures()
    fixtures = suite["fixtures"]

    print(f"Shadow Score Conformance Suite v{suite['conformance_suite_version']}")
    print(f"Testing: {args.validator}")
    print(f"Fixtures: {len(fixtures)}")
    print()

    passed = 0
    failed = 0

    for fixture in fixtures:
        ok, errors = run_fixture(args.validator, fixture)
        if ok:
            passed += 1
            if args.verbose:
                print(f"  ✅ {fixture['id']}: {fixture['description']}")
        else:
            failed += 1
            print(f"  ❌ {fixture['id']}: {fixture['description']}")
            for err in errors:
                print(f"     → {err}")

    print()
    print(f"Results: {passed}/{passed + failed} passed", end="")
    if failed:
        print(f" ({failed} failed)")
    else:
        print(" ✅ All conformant")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
