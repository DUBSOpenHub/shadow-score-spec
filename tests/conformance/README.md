# Conformance Test Suite

Black-box conformance tests for Shadow Score validators. Any validator implementing the Shadow Score Spec v2.0.0 must produce matching output and exit codes for these fixtures.

## What's Here

- **`fixtures.json`** — 18 test fixtures with input, expected JSON output, and expected exit codes
- **`run_conformance.py`** — Runner that tests any validator CLI against the fixtures

## Fixture Categories

| Category | Count | What's Tested |
|----------|-------|---------------|
| Examples (sealed only) | 3 | All 3 worked examples: 0%, 11.1%, 60% |
| Examples (sealed + open) | 3 | Same examples with open tests and coverage_comparison |
| Edge cases | 6 | Zero tests, all-pass, all-fail, single test, boundary levels |
| Thresholds | 5 | Under, over, exact boundary, zero threshold |

## Usage

```bash
# Test the Python reference validator (default)
python tests/conformance/run_conformance.py -v

# Test the Go validator
cd validators && go build -o shadow-score-go .
cd ..
python tests/conformance/run_conformance.py --validator "./validators/shadow-score-go" -v

# Test your own validator
python tests/conformance/run_conformance.py --validator "./my-validator" -v
```

## Writing a New Validator

Your validator is conformant if `run_conformance.py` reports all 18 fixtures passing. The runner checks:

1. **JSON output** — `shadow_score`, `level`, `sealed_tests` counts, failure count, `coverage_comparison` keys
2. **Exit codes** — `0` when under threshold (or no threshold), `1` when exceeded

Required CLI interface:
```
your-validator --sealed <file> [--open <file>] [--threshold <float>] [--format json|summary]
```
