# Agents

## Overview

Shadow Score Spec is a framework-agnostic specification and reference validator library — not a Copilot CLI agent itself. However, Shadow Score is used as the built-in quality measurement protocol by several DUBSOpenHub agents (notably [Terminal Stampede](https://github.com/DUBSOpenHub/terminal-stampede) and [Dark Factory](https://github.com/DUBSOpenHub/dark-factory)). This document describes the validators shipped in this repo and how Copilot can assist with implementing the Shadow Score protocol.

## Available Validators (Reference Implementations)

### shadow-score.py (Python Validator)

- **Purpose**: Computes a Shadow Score from sealed and open test result files. Framework-agnostic — works with any test runner that can produce JSON output.
- **Usage**:
  ```bash
  python validators/shadow-score.py \
    --sealed results-sealed.json \
    --open results-open.json
  ```
- **Output**: Numeric score (0–100%), conformance level (L1–L4), and a JSON report matching the [shadow-report-schema.json](validators/shadow-report-schema.json)

### shadow-score-go (Go Validator)

- **Purpose**: Same computation as the Python validator, implemented in Go for performance or environments where Python is unavailable.
- **Usage**:
  ```bash
  cd validators && go build -o shadow-score-go .
  ./validators/shadow-score-go \
    --sealed results-sealed.json \
    --open results-open.json
  ```

### shadow-score.sh (Shell Validator)

- **Purpose**: Minimal-dependency shell implementation for CI environments or systems without Python or Go.
- **Usage**:
  ```bash
  ./validators/shadow-score.sh results-sealed.txt results-open.txt
  ```

## The Shadow Score Protocol

Shadow Score is computed using the **Sealed-Envelope Protocol**:

```
SPEC → SEAL GENERATION → IMPLEMENTATION → VALIDATION → HARDENING
       (tests from spec,    (code + own       (run both     (fix from
        hidden from          tests, never      suites,      failure msgs
        implementer)         sees sealed)      compute gap) only)
```

**Formula**: `Shadow Score = (sealed_failures / sealed_total) × 100`

| Score | Level | Meaning |
|-------|-------|---------|
| 0% | ✅ Perfect | Implementation covered everything |
| 1–15% | 🟢 Minor | Small blind spots |
| 16–30% | 🟡 Moderate | Meaningful gaps |
| 31–50% | 🟠 Significant | Major gaps |
| >50% | 🔴 Critical | Fundamental quality issues |

## Authorship Independence (v2.0.0)

Hiding the tests answers *"can the implementer see them."* It does not answer *"does the implementer think like the test author."* Where both roles are filled by the same model family, their blind spots correlate: the sealed test for a bug is never written, the score reads 0%, and the bug ships green. **That bias always points toward overclaiming quality.**

Level 4 requires the Seal Author and the Implementer to be drawn from different model families. The rule follows bias direction rather than demanding every role differ:

| Pairing | Bias | Verdict |
|---|---|---|
| Seal Author == Implementer | too low | forbidden |
| Specifier == Implementer | too low | forbidden |
| Specifier == Seal Author | too high | allowed, must be disclosed |
| Validator == anyone | none | unconstrained — it executes, it does not author |

See [§3.6](SPEC.md#36-authorship-independence).

## Using GitHub Copilot with This Repo

Copilot can assist with:
- **Generating sealed tests** from a specification: "Write sealed acceptance tests for this spec — tests only, no implementation"
- **Implementing Shadow Score** in a new language: "Port the shadow-score.py validator to TypeScript"
- **Integrating into CI**: "Add Shadow Score computation to this GitHub Actions workflow"
- **Interpreting results**: "My Shadow Score is 35%. What does that mean and where do I start fixing?"
- **Writing the spec**: "Help me write a formal specification for this feature that can be used to generate sealed tests"

## Configuration

- No runtime dependencies for the shell validator; Python 3.x for the Python validator; Go 1.18+ for the Go validator
- Output format is specified in `validators/shadow-report-schema.json`
- Conformance levels (L1–L4) are defined in [SPEC.md](SPEC.md#6-conformance-levels)
- The critical rule: **the implementer must never see sealed test source code** — only failure messages (test name, expected, actual) during hardening
