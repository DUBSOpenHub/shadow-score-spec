#!/usr/bin/env python3
"""
Tests for shadow-score.py reference validator.

Run with:
    cd validators && python -m unittest test_shadow_score -v
    cd validators && python -m pytest test_shadow_score.py -v
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VALIDATORS_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = VALIDATORS_DIR.parent / "examples"
SCRIPT = VALIDATORS_DIR / "shadow-score.py"


def _load_module():
    """Import shadow-score.py (hyphenated name) via importlib."""
    spec = importlib.util.spec_from_file_location("shadow_score", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(*args):
    """Run shadow-score.py with the given CLI arguments."""
    cmd = [sys.executable, str(SCRIPT)] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def make_sealed_json(total: int, failed: int, category: str = "happy_path") -> dict:
    """Build a minimal sealed-results dict with the requested pass/fail counts."""
    tests = [
        {"name": f"test_pass_{i}", "status": "passed", "category": category}
        for i in range(total - failed)
    ]
    tests += [
        {"name": f"test_fail_{i}", "status": "failed", "category": category,
         "expected": "ok", "actual": "error", "message": f"failure {i}"}
        for i in range(failed)
    ]
    return {"tests": tests}


# ---------------------------------------------------------------------------
# Unit tests: classify_gap
# ---------------------------------------------------------------------------

class TestClassifyGap(unittest.TestCase):
    def setUp(self):
        self.mod = _load_module()

    def test_perfect_zero(self):
        self.assertEqual(self.mod.classify_gap(0.0)[0], "perfect")

    def test_minor_just_above_zero(self):
        self.assertEqual(self.mod.classify_gap(0.1)[0], "minor")

    def test_minor_at_boundary(self):
        self.assertEqual(self.mod.classify_gap(15.0)[0], "minor")

    def test_minor_mid(self):
        self.assertEqual(self.mod.classify_gap(7.5)[0], "minor")

    def test_moderate_just_above_minor(self):
        self.assertEqual(self.mod.classify_gap(15.1)[0], "moderate")

    def test_moderate_at_boundary(self):
        self.assertEqual(self.mod.classify_gap(30.0)[0], "moderate")

    def test_significant_just_above_moderate(self):
        self.assertEqual(self.mod.classify_gap(30.1)[0], "significant")

    def test_significant_at_boundary(self):
        self.assertEqual(self.mod.classify_gap(50.0)[0], "significant")

    def test_critical_just_above_significant(self):
        self.assertEqual(self.mod.classify_gap(50.1)[0], "critical")

    def test_critical_at_100(self):
        self.assertEqual(self.mod.classify_gap(100.0)[0], "critical")

    def test_indicators_present(self):
        _, ind = self.mod.classify_gap(0.0)
        self.assertIn(ind, ["✅", "🟢", "🟡", "🟠", "🔴"])


# ---------------------------------------------------------------------------
# Unit tests: compute_shadow_score
# ---------------------------------------------------------------------------

class TestComputeShadowScore(unittest.TestCase):
    def setUp(self):
        self.mod = _load_module()

    def test_zero_sealed_tests(self):
        result = self.mod.compute_shadow_score([])
        self.assertEqual(result["shadow_score"], 0.0)
        self.assertEqual(result["level"], "perfect")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["failures"], [])

    def test_all_pass(self):
        tests = [{"name": f"t{i}", "status": "passed", "category": "happy_path"} for i in range(10)]
        result = self.mod.compute_shadow_score(tests)
        self.assertEqual(result["shadow_score"], 0.0)
        self.assertEqual(result["level"], "perfect")
        self.assertEqual(result["passed"], 10)
        self.assertEqual(result["failed"], 0)

    def test_all_fail(self):
        tests = [{"name": f"t{i}", "status": "failed", "category": "error_handling"} for i in range(5)]
        result = self.mod.compute_shadow_score(tests)
        self.assertEqual(result["shadow_score"], 100.0)
        self.assertEqual(result["level"], "critical")
        self.assertEqual(result["failed"], 5)
        self.assertEqual(result["passed"], 0)
        self.assertEqual(len(result["failures"]), 5)

    def test_partial_failures_moderate(self):
        # 2/10 = 20% → moderate
        tests = [{"name": f"p{i}", "status": "passed"} for i in range(8)]
        tests += [{"name": f"f{i}", "status": "failed"} for i in range(2)]
        result = self.mod.compute_shadow_score(tests)
        self.assertEqual(result["shadow_score"], 20.0)
        self.assertEqual(result["level"], "moderate")

    def test_score_rounded_to_one_decimal(self):
        # 1/3 = 33.333... → 33.3
        tests = [{"name": f"p{i}", "status": "passed"} for i in range(2)]
        tests += [{"name": "f0", "status": "failed"}]
        result = self.mod.compute_shadow_score(tests)
        self.assertEqual(result["shadow_score"], 33.3)

    def test_failures_list_contains_only_failed(self):
        tests = [
            {"name": "pass1", "status": "passed"},
            {"name": "fail1", "status": "failed", "message": "oops"},
        ]
        result = self.mod.compute_shadow_score(tests)
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["failures"][0]["name"], "fail1")


# ---------------------------------------------------------------------------
# Integration tests: worked examples
# ---------------------------------------------------------------------------

def _examples_exist(subdir: str) -> bool:
    return (EXAMPLES_DIR / subdir / "sealed-results.json").exists()


class TestWorkedExamples(unittest.TestCase):
    @unittest.skipUnless(_examples_exist("01-perfect-score"), "example files not found")
    def test_example_01_perfect_score(self):
        sealed = str(EXAMPLES_DIR / "01-perfect-score" / "sealed-results.json")
        open_f = str(EXAMPLES_DIR / "01-perfect-score" / "open-results.json")
        result = run_cli("--sealed", sealed, "--open", open_f)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["report"]["shadow_score"], 0.0)
        self.assertEqual(report["report"]["level"], "perfect")
        self.assertEqual(report["sealed_tests"]["failed"], 0)

    @unittest.skipUnless(_examples_exist("02-minor-gaps"), "example files not found")
    def test_example_02_minor_gaps(self):
        sealed = str(EXAMPLES_DIR / "02-minor-gaps" / "sealed-results.json")
        result = run_cli("--sealed", sealed)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["report"]["shadow_score"], 11.1)
        self.assertEqual(report["report"]["level"], "minor")

    @unittest.skipUnless(_examples_exist("03-critical-gaps"), "example files not found")
    def test_example_03_critical_gaps(self):
        sealed = str(EXAMPLES_DIR / "03-critical-gaps" / "sealed-results.json")
        result = run_cli("--sealed", sealed)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["report"]["shadow_score"], 60.0)
        self.assertEqual(report["report"]["level"], "critical")

    @unittest.skipUnless(_examples_exist("01-perfect-score"), "example files not found")
    def test_example_01_open_tests_included_in_report(self):
        sealed = str(EXAMPLES_DIR / "01-perfect-score" / "sealed-results.json")
        open_f = str(EXAMPLES_DIR / "01-perfect-score" / "open-results.json")
        result = run_cli("--sealed", sealed, "--open", open_f)
        report = json.loads(result.stdout)
        self.assertIn("open_tests", report)
        self.assertIn("coverage_comparison", report)


# ---------------------------------------------------------------------------
# Integration tests: threshold exit codes
# ---------------------------------------------------------------------------

class TestThreshold(unittest.TestCase):
    def _write_temp(self, data: dict) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, f)
        f.close()
        return f.name

    def test_under_threshold_exits_zero(self):
        # 10% shadow score, threshold 15 → should pass
        fname = self._write_temp(make_sealed_json(10, 1))
        try:
            result = run_cli("--sealed", fname, "--threshold", "15")
            self.assertEqual(result.returncode, 0)
        finally:
            os.unlink(fname)

    def test_over_threshold_exits_one(self):
        # 50% shadow score, threshold 15 → should fail
        fname = self._write_temp(make_sealed_json(10, 5))
        try:
            result = run_cli("--sealed", fname, "--threshold", "15")
            self.assertEqual(result.returncode, 1)
        finally:
            os.unlink(fname)

    def test_exactly_at_threshold_exits_zero(self):
        # Exactly 10% shadow score, threshold 10 → 10 > 10 is False → exit 0
        fname = self._write_temp(make_sealed_json(10, 1))
        try:
            result = run_cli("--sealed", fname, "--threshold", "10")
            self.assertEqual(result.returncode, 0)
        finally:
            os.unlink(fname)

    def test_no_threshold_always_exits_zero(self):
        # 100% shadow score with no threshold → still exit 0
        fname = self._write_temp(make_sealed_json(10, 10))
        try:
            result = run_cli("--sealed", fname)
            self.assertEqual(result.returncode, 0)
        finally:
            os.unlink(fname)

    def test_threshold_zero_fails_any_failure(self):
        # Even one failure with threshold 0 → exit 1
        fname = self._write_temp(make_sealed_json(10, 1))
        try:
            result = run_cli("--sealed", fname, "--threshold", "0")
            self.assertEqual(result.returncode, 1)
        finally:
            os.unlink(fname)

    def test_threshold_zero_passes_perfect(self):
        fname = self._write_temp(make_sealed_json(5, 0))
        try:
            result = run_cli("--sealed", fname, "--threshold", "0")
            self.assertEqual(result.returncode, 0)
        finally:
            os.unlink(fname)


# ---------------------------------------------------------------------------
# Integration tests: output formats
# ---------------------------------------------------------------------------

class TestOutputFormats(unittest.TestCase):
    def setUp(self):
        self._tmp_files = []

    def tearDown(self):
        for f in self._tmp_files:
            try:
                os.unlink(f)
            except FileNotFoundError:
                pass

    def _write_temp(self, data: dict) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, f)
        f.close()
        self._tmp_files.append(f.name)
        return f.name

    def test_json_output_is_valid_json(self):
        fname = self._write_temp(make_sealed_json(4, 1))
        result = run_cli("--sealed", fname, "--format", "json")
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)  # must not raise
        self.assertIsInstance(report, dict)

    def test_json_output_has_required_keys(self):
        fname = self._write_temp(make_sealed_json(4, 1))
        result = run_cli("--sealed", fname, "--format", "json")
        report = json.loads(result.stdout)
        for key in ("shadow_score_spec_version", "report", "sealed_tests", "failures"):
            self.assertIn(key, report, f"missing key: {key}")

    def test_json_spec_version_matches(self):
        fname = self._write_temp(make_sealed_json(4, 0))
        result = run_cli("--sealed", fname)
        report = json.loads(result.stdout)
        self.assertEqual(report["shadow_score_spec_version"], "2.0.0")

    def test_json_failures_is_list(self):
        fname = self._write_temp(make_sealed_json(4, 2))
        result = run_cli("--sealed", fname)
        report = json.loads(result.stdout)
        self.assertIsInstance(report["failures"], list)
        self.assertEqual(len(report["failures"]), 2)

    def test_json_empty_failures_is_empty_list_not_null(self):
        fname = self._write_temp(make_sealed_json(4, 0))
        result = run_cli("--sealed", fname)
        report = json.loads(result.stdout)
        self.assertEqual(report["failures"], [])

    def test_summary_output_contains_shadow_score_line(self):
        fname = self._write_temp(make_sealed_json(4, 1))
        result = run_cli("--sealed", fname, "--format", "summary")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Shadow Score:", result.stdout)

    def test_summary_output_contains_sealed_line(self):
        fname = self._write_temp(make_sealed_json(4, 1))
        result = run_cli("--sealed", fname, "--format", "summary")
        self.assertIn("Sealed:", result.stdout)

    def test_summary_output_lists_failures(self):
        fname = self._write_temp(make_sealed_json(4, 2, "security"))
        result = run_cli("--sealed", fname, "--format", "summary")
        self.assertIn("Failures", result.stdout)
        self.assertIn("❌", result.stdout)

    def test_json_with_open_includes_open_tests(self):
        sealed_f = self._write_temp(make_sealed_json(4, 1))
        open_f = self._write_temp(make_sealed_json(3, 0))
        result = run_cli("--sealed", sealed_f, "--open", open_f)
        report = json.loads(result.stdout)
        self.assertIn("open_tests", report)
        self.assertEqual(report["open_tests"]["total"], 3)

    def test_json_with_open_includes_coverage_comparison(self):
        sealed_f = self._write_temp(make_sealed_json(4, 1, "security"))
        open_f = self._write_temp(make_sealed_json(3, 0, "happy_path"))
        result = run_cli("--sealed", sealed_f, "--open", open_f)
        report = json.loads(result.stdout)
        self.assertIn("coverage_comparison", report)
        comparison = report["coverage_comparison"]
        self.assertIn("security", comparison)
        self.assertIn("edge_case", comparison)

    def test_summary_with_open_includes_open_line(self):
        sealed_f = self._write_temp(make_sealed_json(4, 0))
        open_f = self._write_temp(make_sealed_json(6, 0))
        result = run_cli("--sealed", sealed_f, "--open", open_f, "--format", "summary")
        self.assertIn("Open:", result.stdout)


# ---------------------------------------------------------------------------
# Edge-case: missing --sealed flag
# ---------------------------------------------------------------------------

class TestCLIErrors(unittest.TestCase):
    def test_missing_sealed_flag_exits_nonzero(self):
        result = run_cli()  # no arguments
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
