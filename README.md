# 📊 Shadow Score Spec

[![Spec Version](https://img.shields.io/badge/spec-v2.0.0-blue.svg)](SPEC.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Conformance Levels](https://img.shields.io/badge/conformance-L1%20%7C%20L2%20%7C%20L3%20%7C%20L4-green.svg)](SPEC.md#6-conformance-levels)

**A framework-agnostic metric for measuring AI code generation quality.**

---

## The Problem

AI coding tools write code and tests together. The tests always pass — but they only validate what the AI *thought* to check, not what the *specification actually requires*. There's no independent quality signal.

## The Solution

```
Shadow Score = (sealed_failures / sealed_total) × 100
```

Generate acceptance tests from the spec **before code exists**. Hide them from the AI. Build the code. Then run both test suites. The delta is your **Shadow Score** — an adversarial, quantitative measure of implementation quality.

## Interpretation Scale

| Score | Level | Meaning |
|-------|-------|---------|
| 0% | ✅ Perfect | Implementation tests covered everything |
| 1–15% | 🟢 Minor | Small blind spots — edge cases |
| 16–30% | 🟡 Moderate | Meaningful gaps in coverage |
| 31–50% | 🟠 Significant | Major gaps — review approach |
| >50% | 🔴 Critical | Fundamental quality issues |

## Why "Shadow Score"?

*Shadow Score measures what your AI missed when it couldn't see the tests.*
**Shadow Score** sticks because it maps to something developers already know: *shadow testing* — running hidden checks alongside production to catch what the main path misses. That's exactly what sealed-envelope testing does. The AI builds code. Shadow tests — written before the code existed and hidden from the builder — judge it. Whatever fails is what the AI couldn't see.

**0% = no shadows.** The implementation covered everything the spec required.  
**60% = flying blind.** The AI missed more than half the acceptance criteria it never knew about.

## Quick Start: Add Shadow Score in 5 Minutes

### Option A: Use the reference validators

```bash
# Python
python validators/shadow-score.py --sealed results-sealed.json --open results-open.json

# Go
cd validators && go build -o shadow-score-go . && cd ..
./validators/shadow-score-go --sealed results-sealed.json --open results-open.json

# Shell (minimal deps)
./validators/shadow-score.sh results-sealed.txt results-open.txt
```

### Option B: Compute it yourself

1. **Write sealed tests** from your spec (requirements → test cases, before code exists) — using a *different model family* than the one that will implement
2. **Build the code** — the implementer never sees the sealed tests
3. **Run both suites** — in a disposable workspace built from the implementer's commit
4. **Compute**: `failed_sealed / total_sealed × 100`
5. **Report**: Use the [JSON schema](validators/shadow-report-schema.json) or markdown format, including which families authored each side

That's it. Framework, language, and tooling don't matter — Shadow Score works anywhere.

## The Sealed-Envelope Protocol

Shadow Score is computed using the **Sealed-Envelope Protocol** — a 4-phase testing methodology:

```
 SPEC ──► SEAL GENERATION ──► IMPLEMENTATION ──► VALIDATION ──► HARDENING
           (tests from spec,     (code + own        (run both      (fix from
            hidden from          tests, never       suites in a   failure msgs
            implementer,         sees sealed)       disposable    only — no
            different model                        workspace)     test code)
            family)
```

**The two critical rules:**

1. **Isolation** — the implementer **never sees** the sealed tests. During hardening it receives only failure messages (test name, expected, actual), never test source. This forces root-cause fixes, not test-targeting hacks.
2. **Independence** — the sealed tests are written by a **different model family** than the implementation. Isolation stops the builder seeing the tests; it does not stop it thinking like their author. Same-family agents share blind spots, so the scenario nobody tested is the scenario nobody handled.

Full protocol details: [**SPEC.md §4**](SPEC.md#4-sealed-envelope-protocol)

## Conformance Levels

| Level | What's Required | Use Case |
|-------|----------------|----------|
| **L1** — Shadow Score | Compute + report Shadow Score | Retrofitting onto existing test suites |
| **L2** — Sealed Envelope | L1 + test isolation + tamper hash | AI agent pipelines |
| **L3** — Full Protocol | L2 + hardening loop + velocity tracking | Production autonomous builds |
| **L4** — Adversarial Independence | L3 + cross-family authorship + disposable verify workspace + provenance in report | Published or gate-blocking scores |

**Why L4 exists:** L1–L3 harden *information* isolation — they stop the builder from **seeing** the tests. They are all silently defeated by one configuration choice: pointing the seal author and the implementer at the same model. Same-family agents share blind spots, so the untested defect is also the unhandled defect. The sealed test is never written, the score reads 0%, and the bug ships green. That bias is directional — it always overclaims quality. See [**SPEC.md §3.6**](SPEC.md#36-authorship-independence).

## Reference Implementations

The reference Level 4 implementation is **[Dark Factory](https://github.com/DUBSOpenHub/dark-factory)** — an autonomous agentic build system for the GitHub Copilot CLI with sealed-envelope testing, cross-family model independence enforced pre-dispatch, and seal plurality.

The reference Level 2 implementation is **[Terminal Stampede](https://github.com/DUBSOpenHub/terminal-stampede)** — a parallel agent runtime that shadow-scores each agent's work during merge using sealed tests with tamper-hash verification.

## Worked Examples

| Example | Shadow Score | What Happened |
|---------|-----------|---------------|
| [01 — Perfect Score](examples/01-perfect-score/) | 0% ✅ | All sealed tests passed |
| [02 — Minor Gaps](examples/02-minor-gaps/) | 11.1% 🟢 | 2 edge cases missed |
| [03 — Critical Gaps](examples/03-critical-gaps/) | 60% 🔴 | Only happy path tested |

## Reporting Format

Shadow Reports can be produced in JSON (machine-readable) or Markdown (human-readable).

**JSON schema:** [`validators/shadow-report-schema.json`](validators/shadow-report-schema.json)

```json
{
  "shadow_score_spec_version": "2.0.0",
  "report": {
    "shadow_score": 11.1,
    "level": "minor",
    "conformance_level": 4,
    "independence": "strong",
    "implementer_family": "anthropic",
    "seal_author_families": ["openai", "google"],
    "workspace_isolation": "strict"
  },
  "sealed_tests": { "total": 18, "passed": 16, "failed": 2 },
  "failures": [
    {
      "test_name": "test_rejects_gpl_dependency",
      "category": "security",
      "expected": "exit code 2",
      "actual": "exit code 0",
      "message": "GPL dependency not blocked"
    }
  ]
}
```

A Shadow Score without provenance cannot be interpreted: 0% under `strong` independence and 0% under `weak` independence are different claims about the world, and only one of them is evidence.

Full schema: [**SPEC.md §5**](SPEC.md#5-reporting-format)

## Adopters

| Project | Conformance | Description |
|---------|-------------|-------------|
| [Dark Factory](https://github.com/DUBSOpenHub/dark-factory) | Level 4 | Reference implementation — autonomous agentic build system with cross-family adversarial independence |
| [Terminal Stampede](https://github.com/DUBSOpenHub/terminal-stampede) | Level 2 | Parallel agent runtime — shadow-scores each agent's work during merge via sealed tests |

*Using Shadow Score? [Open a PR](https://github.com/DUBSOpenHub/shadow-score-spec/pulls) to add your project.*

## Full Specification

📄 **[Read the full spec →](SPEC.md)**

Covers: definitions, formula, sealed-envelope protocol, reporting format, conformance levels, worked examples, and FAQ.

## Contributing

Shadow Score is an open specification. Contributions welcome:

- **Spec changes**: Open an issue to discuss before submitting a PR
- **New validators**: PRs for additional language validators (Go, Rust, TypeScript) are welcome
- **Adopter listings**: Add your project to the Adopters table

## License

[MIT](LICENSE) © 2026 DUBSOpenHub