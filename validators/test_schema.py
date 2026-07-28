#!/usr/bin/env python3
"""
Schema conformance tests for shadow-report-schema.json.

These guard the rules that a permissive schema would otherwise wave through.
The failure mode they exist to prevent is specific and quiet: a report that
claims Level 4 while carrying provenance the validator never actually checked,
because the field was misspelled or written at the wrong depth. That produces a
green conformance claim with nothing behind it.

Run: python3 validators/test_schema.py
"""

import json
import os
import unittest

from jsonschema import Draft7Validator

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "shadow-report-schema.json")

with open(SCHEMA_PATH) as fh:
    SCHEMA = json.load(fh)

VALIDATOR = Draft7Validator(SCHEMA)

ENVELOPE = {
    "shadow_score_spec_version": "2.0.0",
    "sealed_tests": {"total": 18, "passed": 16, "failed": 2},
    "failures": [],
}

LEVEL_4_REPORT = {
    "shadow_score": 11.1,
    "level": "minor",
    "conformance_level": 4,
    "independence": "strong",
    "implementer_family": "anthropic",
    "implementer_model": "claude-opus-4.8",
    "seal_author_families": ["openai", "google"],
    "seal_author_models": ["gpt-5.6-terra", "gemini-3.1-pro-preview"],
    "workspace_isolation": "strict",
    "seal_broken": False,
}


def doc(report=None, **root):
    """Build a report document from the standard envelope."""
    out = dict(ENVELOPE, **root)
    if report is not None:
        out["report"] = report
    return out


class SchemaTestCase(unittest.TestCase):
    def assertValid(self, instance, msg=""):
        errors = sorted(VALIDATOR.iter_errors(instance), key=str)
        if errors:
            self.fail(f"{msg or 'expected valid'}: {errors[0].message[:200]}")

    def assertInvalid(self, instance, at=None, msg=""):
        errors = list(VALIDATOR.iter_errors(instance))
        self.assertTrue(errors, msg or "expected the schema to reject this document")
        if at is not None:
            paths = {"/".join(str(p) for p in e.absolute_path) for e in errors}
            self.assertIn(at, paths, f"expected an error at {at!r}, got {sorted(paths)}")


class TestSchemaItself(SchemaTestCase):
    def test_schema_is_well_formed_draft7(self):
        Draft7Validator.check_schema(SCHEMA)

    def test_schema_declares_current_spec_version(self):
        self.assertIn("v2.0.0", SCHEMA["description"])


class TestBaselineReports(SchemaTestCase):
    def test_level_4_report_is_valid(self):
        self.assertValid(doc(LEVEL_4_REPORT))

    def test_minimal_report_is_valid(self):
        self.assertValid(doc({"shadow_score": 0.0, "level": "perfect"}))

    def test_v1_era_report_still_validates(self):
        """v2.0.0 adds fields; it must not invalidate conforming v1.0.0 reports."""
        self.assertValid(
            doc({"shadow_score": 11.1, "level": "minor", "sealed_hash": "sha256:abc"})
        )

    def test_unknown_fields_are_allowed(self):
        """Vendor extensions are permitted; only listed fields are constrained."""
        self.assertValid(doc({**LEVEL_4_REPORT, "vendor_x_custom": {"anything": 1}}))


class TestLevel4Provenance(SchemaTestCase):
    def test_level_4_requires_independence(self):
        report = {k: v for k, v in LEVEL_4_REPORT.items() if k != "independence"}
        self.assertInvalid(doc(report), at="report")

    def test_level_4_requires_implementer_family(self):
        report = {k: v for k, v in LEVEL_4_REPORT.items() if k != "implementer_family"}
        self.assertInvalid(doc(report), at="report")

    def test_level_4_requires_seal_author_families(self):
        report = {k: v for k, v in LEVEL_4_REPORT.items() if k != "seal_author_families"}
        self.assertInvalid(doc(report), at="report")

    def test_lower_levels_do_not_require_provenance(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                self.assertValid(
                    doc({"shadow_score": 0.0, "level": "perfect", "conformance_level": level})
                )

    def test_independence_enum_is_closed(self):
        self.assertInvalid(doc({**LEVEL_4_REPORT, "independence": "medium"}))

    def test_conformance_level_is_bounded(self):
        self.assertInvalid(doc({**LEVEL_4_REPORT, "conformance_level": 5}))


class TestDriftGuards(SchemaTestCase):
    """The reference implementation drifted on exactly these two points."""

    def test_renamed_seal_families_is_rejected(self):
        report = {k: v for k, v in LEVEL_4_REPORT.items() if k != "seal_author_families"}
        report["seal_families"] = ["openai", "google"]
        self.assertInvalid(doc(report), at="report/seal_families")

    def test_seal_families_rejected_even_alongside_correct_field(self):
        self.assertInvalid(
            doc({**LEVEL_4_REPORT, "seal_families": ["openai"]}),
            at="report/seal_families",
        )

    def test_conformance_level_at_root_is_rejected(self):
        """At the root it is invisible to the Level 4 conditional."""
        report = {k: v for k, v in LEVEL_4_REPORT.items() if k != "conformance_level"}
        self.assertInvalid(doc(report, conformance_level=4), at="conformance_level")

    def test_misplaced_provenance_fields_are_rejected(self):
        for field, value in [
            ("independence", "strong"),
            ("implementer_family", "anthropic"),
            ("seal_author_families", ["openai"]),
            ("shadow_score", 11.1),
            ("advisory", True),
        ]:
            with self.subTest(field=field):
                self.assertInvalid(doc(LEVEL_4_REPORT, **{field: value}), at=field)

    def test_full_regression_case(self):
        """The exact shape that passed the pre-hardening schema."""
        bad = doc(
            {
                "shadow_score": 11.1,
                "level": "minor",
                "independence": "strong",
                "seal_families": ["openai", "google"],
                "implementer_family": "anthropic",
            },
            conformance_level=4,
        )
        errors = list(VALIDATOR.iter_errors(bad))
        paths = {"/".join(str(p) for p in e.absolute_path) for e in errors}
        self.assertIn("conformance_level", paths)
        self.assertIn("report/seal_families", paths)


class TestAdvisoryRules(SchemaTestCase):
    """SPEC.md section 5.4 — conditions that make a score non-authoritative."""

    def test_advisory_requires_a_reason(self):
        self.assertInvalid(doc({**LEVEL_4_REPORT, "advisory": True}), at="report")

    def test_advisory_with_reason_is_valid(self):
        self.assertValid(
            doc({**LEVEL_4_REPORT, "advisory": True, "advisory_reason": "weak independence"})
        )

    def test_weak_independence_must_be_advisory(self):
        self.assertInvalid(doc({**LEVEL_4_REPORT, "independence": "weak"}), at="report")

    def test_weak_independence_marked_advisory_is_valid(self):
        self.assertValid(
            doc(
                {
                    **LEVEL_4_REPORT,
                    "independence": "weak",
                    "advisory": True,
                    "advisory_reason": "seal author and implementer share a model family",
                }
            )
        )

    def test_broken_seal_must_be_advisory(self):
        self.assertInvalid(doc({**LEVEL_4_REPORT, "seal_broken": True}), at="report")

    def test_broken_seal_marked_advisory_is_valid(self):
        self.assertValid(
            doc(
                {
                    **LEVEL_4_REPORT,
                    "seal_broken": True,
                    "advisory": True,
                    "advisory_reason": "canary access time changed before validation",
                }
            )
        )


class TestValueConstraints(SchemaTestCase):
    def test_shadow_score_is_bounded(self):
        self.assertInvalid(doc({**LEVEL_4_REPORT, "shadow_score": 101}))
        self.assertInvalid(doc({**LEVEL_4_REPORT, "shadow_score": -1}))

    def test_spec_ambiguity_is_a_ratio(self):
        self.assertValid(doc({**LEVEL_4_REPORT, "spec_ambiguity": 0.25}))
        self.assertInvalid(doc({**LEVEL_4_REPORT, "spec_ambiguity": 25}))

    def test_workspace_isolation_enum(self):
        self.assertValid(doc({**LEVEL_4_REPORT, "workspace_isolation": "legacy"}))
        self.assertInvalid(doc({**LEVEL_4_REPORT, "workspace_isolation": "none"}))

    def test_seal_author_families_must_be_unique_and_non_empty(self):
        self.assertInvalid(doc({**LEVEL_4_REPORT, "seal_author_families": []}))
        self.assertInvalid(
            doc({**LEVEL_4_REPORT, "seal_author_families": ["openai", "openai"]})
        )

    def test_max_reveal_never_includes_test_source(self):
        """SPEC.md section 4.4.1 — disclosure stops at assertion values."""
        self.assertValid(doc(LEVEL_4_REPORT, hardening={"max_reveal": "assertion"}))
        self.assertInvalid(doc(LEVEL_4_REPORT, hardening={"max_reveal": "source"}))

    def test_level_enum_is_closed(self):
        self.assertInvalid(doc({**LEVEL_4_REPORT, "level": "catastrophic"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
