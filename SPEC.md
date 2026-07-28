# Shadow Score Specification

**Version:** 2.0.0  
**Status:** Draft  
**Date:** 2026-07-28  
**Authors:** DUBSOpenHub  
**License:** MIT  

---

## 1. Abstract

**Shadow Score** is a framework-agnostic metric for measuring the quality of AI-generated code. It quantifies the difference between what an AI implementation agent *tested for itself* and what an independent, specification-derived test suite *actually requires*. A Shadow Score of 0% means the implementation's own tests fully anticipated the acceptance criteria. A high Shadow Score reveals blind spots — requirements the AI "thought" it covered but didn't.

Shadow Score is computed using the **Sealed-Envelope Protocol**, a testing methodology where acceptance tests are generated from the specification *before code is written* and hidden from the implementation agent throughout the build process.

---

## 2. Motivation

### The Teach-to-Test Problem

Most AI coding tools write code and tests together. The AI generates an implementation, then writes tests that validate *what it built* — not *what was required*. These tests almost always pass, creating a false sense of quality.

This is analogous to a student writing both the exam and the answer key. A 100% score is guaranteed but meaningless.

### What's Missing

The industry lacks a standardized, quantitative metric for answering: **"How well did the AI understand and implement the specification, independent of its own self-assessment?"**

Existing metrics fall short:

| Metric | Limitation |
|--------|-----------|
| Test pass rate | AI writes tests to match its own code — circular |
| Code coverage | Measures lines executed, not requirements fulfilled |
| Human code review | Subjective, expensive, doesn't scale |
| LLM-as-judge | Another AI evaluating AI — same blindness risk |

### Shadow Score Solves This

Shadow Score introduces an **independent, adversarial quality signal** by separating test authorship from code authorship and measuring the delta. It answers a specific question: *"What percentage of specification requirements did the implementation fail to satisfy, as measured by tests the implementer never saw?"*

---

## 3. Definitions

### 3.1 Roles

| Role | Responsibility | Information Access |
|------|---------------|-------------------|
| **Specifier** | Produces the specification (requirements, acceptance criteria) | Full project context |
| **Seal Author** | Generates specification tests (sealed tests) from the spec | Specification ONLY — never code, never architecture |
| **Implementer** | Writes code and implementation tests (open tests) | Specification + architecture — NEVER sealed tests |
| **Validator** | Runs all tests and computes Shadow Score | Full access: code + sealed tests + open tests |

In an AI agent pipeline, each role is typically a separate agent invocation with isolated context. In a human workflow, roles may be assigned to different team members.

Roles are also constrained by **authorship independence** (§3.6), which governs *who* — or *which model* — may occupy two roles at once.

### 3.2 Test Suites

- **Sealed Tests** (`S`): Tests generated from the specification before any implementation exists. These tests are hidden from the Implementer. They validate *requirements*, not *implementation details*.

- **Open Tests** (`O`): Tests written by the Implementer alongside the code. These validate the Implementer's own understanding of the requirements.

### 3.3 Shadow Score Formula

```
Shadow Score = (Sf / St) × 100
```

Where:
- `Sf` = Number of sealed tests that **failed**
- `St` = Total number of sealed tests
- Result is expressed as a percentage (0–100)

### 3.4 Interpretation Scale

| Score | Level | Indicator | Meaning |
|-------|-------|-----------|---------|
| 0% | Perfect | ✅ | Implementer's tests covered everything the sealed tests checked |
| 1–15% | Minor | 🟢 | Small blind spots — likely edge cases or boundary conditions |
| 16–30% | Moderate | 🟡 | Meaningful gaps — Implementer missed some scenarios |
| 31–50% | Significant | 🟠 | Major gaps — review the Implementer's testing approach |
| >50% | Critical | 🔴 | Fundamental quality issues — consider re-implementation |

### 3.5 Supplementary Metrics

These optional metrics provide additional context alongside the primary Shadow Score:

- **Coverage Delta**: `|sealed_categories_tested - open_categories_tested|` — measures how many *types* of scenarios (happy path, edge case, error handling, security) differ between suites.
- **Overlap Ratio**: `matching_scenarios / St` — measures how many sealed test scenarios the Implementer independently anticipated.
- **Hardening Velocity**: `(initial_shadow_score - final_shadow_score) / cycles_completed` — Shadow Score points recovered per hardening cycle. Computing it REQUIRES recording `initial_shadow_score` *before* the first hardening cycle; implementations that store only the final score cannot claim Level 3.
- **Spec Ambiguity**: `contradicting_acceptance_criteria / total_acceptance_criteria` — see §4.6. Defined only when seal plurality is used.

### 3.6 Authorship Independence

> A Shadow Score is only meaningful if the tests and the code come from **different minds**.

§4.2 governs *information* isolation: it answers **"can the Implementer see the sealed tests?"** It does not answer **"does the Implementer think like the Seal Author?"**

When the Seal Author and the Implementer are two instances of the same AI model — or the same model family — they share training data, reasoning priors, and therefore **failure modes**. If the family does not think to test a scenario, it also does not think to handle it. The sealed test is never written, the implementation is never hardened, the Shadow Score reads 0%, and the defect ships unflagged.

**This bias is not random. It is directional: it always pushes the Shadow Score toward 0%.** A perfectly isolated pipeline built entirely on one model family systematically *overclaims* quality, and does so most confidently on exactly the requirements neither side considered.

#### 3.6.1 Independence classes

| Class | Definition |
|-------|-----------|
| `strong` | Seal Author and Implementer are different model families (or different humans/teams with no shared authorship) |
| `weak` | Seal Author and Implementer share a model family, or are the same agent |

A Shadow Score produced under `weak` independence MUST be reported as **advisory** and MUST NOT be presented as authoritative (§5.4).

#### 3.6.2 Bias direction by role pair

Not every shared assignment is equally harmful. What matters is the direction in which the resulting bias moves the score.

| Role pair | Effect on Shadow Score | Verdict |
|-----------|-----------------------|---------|
| Seal Author == Implementer | Too **low** — overclaims quality | ❌ MUST NOT |
| Specifier == Implementer | Too **low** — the Implementer infers the Specifier's unstated assumptions | ❌ MUST NOT |
| Specifier == Seal Author | Too **high** — the Seal Author infers them instead | ⚠️ MAY, MUST be disclosed |
| Validator == anyone | No effect — the Validator executes, it does not author | ✅ MAY |

A pairing that biases the score *upward* is conservative: it penalises the Implementer for requirements that were never stated, which is a visible, correctable error. A pairing that biases it *downward* hides defects, which is not.

Blanket "all roles must differ" rules miss this distinction and impose cost where there is no risk.

---

## 4. Sealed-Envelope Protocol

The Sealed-Envelope Protocol is the testing methodology that produces a valid Shadow Score. Implementations MUST follow this protocol to claim Shadow Score conformance.

### 4.1 Seal Generation

**Input:** Specification document (requirements, acceptance criteria, user stories).  
**Output:** Sealed test files written to an isolated location.

Requirements:
1. The Seal Author receives ONLY the specification — never code, architecture, or design documents.
2. Sealed tests MUST validate **behavior**, not implementation details (no testing internal functions, private APIs, or data structures).
3. Sealed tests MUST cover:
   - Happy path scenarios (expected inputs → expected outputs)
   - Edge cases and boundary conditions
   - Error handling and invalid inputs
   - Security scenarios (where applicable)
4. Sealed tests MUST be executable by a standard test runner for the target language/framework.
5. After generation, the sealed test directory SHOULD be hashed (SHA-256) as tamper evidence.

### 4.2 Information Isolation

This is the **first critical invariant** of the protocol. Breaking it invalidates the Shadow Score. The second is authorship independence (§4.2.1).

| Phase | Seal Author Sees | Implementer Sees | Validator Sees |
|-------|-----------------|------------------|---------------|
| Seal Generation | Specification | — | — |
| Implementation | — | Specification, Architecture | — |
| Validation | — | — | Code, Sealed Tests, Open Tests |
| Hardening | — | Failure messages ONLY | Code, All Tests |

**Isolation mechanisms** (in order of strength):
1. **Topological isolation**: Sealed tests are stored outside any directory the Implementer can reach, and are never written into its workspace at any point (strongest — see §4.3)
2. **Process isolation**: Separate OS processes with no shared filesystem access
3. **Context isolation**: Separate AI agent invocations with no shared context (minimum for AI pipelines)
4. **Role isolation**: Different humans/teams with access controls (acceptable for human workflows)
5. **Honor system**: Trust-based separation (weakest — not recommended for conformance claims)

> **Note on agent tooling.** Context isolation alone is insufficient when the Implementer has unscoped filesystem tools (`bash`, `grep`, `glob`). Prompt instructions not to read a directory are not an access control. If the Implementer *can* reach the sealed tests, isolation depends on its compliance, and a Shadow Score that depends on the Implementer's good behaviour measures nothing.

#### 4.2.1 Authorship Independence

Implementations claiming Level 4 (§6) MUST enforce, before any agent is dispatched:

1. The Seal Author and the Implementer are of **different model families** (§3.6.1)
2. The Specifier is not of the Implementer's family
3. Where the roles exist, no reviewer shares a family with the party it reviews (e.g. an architecture critic and the architect; a security reviewer and the Implementer)

Violations MUST either abort the run or force the report to advisory status (§5.4). Silently emitting a score known to be biased is a conformance failure.

**Family assignment** is implementation-defined but MUST be declared, and MUST group models that share pretraining lineage. Two checkpoints of the same base model are the same family regardless of version or size.

### 4.3 Validation

**Input:** Implementation code, sealed tests, open tests.  
**Output:** Shadow Report (see §5).

Procedure:
1. Construct a **disposable verification workspace** from the Implementer's committed output, and place the sealed tests there — never in the Implementer's own workspace
2. Install dependencies and build the project
3. Run sealed tests using the appropriate test runner
4. Run open tests using the appropriate test runner
5. Record: total sealed tests, passed, failed (with failure messages)
6. Record: total open tests, passed, failed
7. Compute Shadow Score: `(sealed_failures / sealed_total) × 100`
8. Categorize failures by type (happy path, edge case, error handling, security)
9. Destroy the verification workspace
10. Produce the Shadow Report

> **Changed in 2.0.0.** v1.0.0 step 1 read *"copy sealed tests into the implementation workspace"*. That is safe only when validation is terminal. In a hardening loop (§4.4) the Implementer is re-invoked **after** validation, and the sealed tests are by then sitting in a directory it can read. Implementations that harden MUST use a disposable workspace. Implementations that validate exactly once MAY use the v1.0.0 copy-in/delete-after procedure and MUST declare `workspace_isolation: "legacy"` in the report.

### 4.4 Hardening

When Shadow Score > 0%, the Implementer may fix the code iteratively. The hardening loop preserves information isolation:

1. Record `initial_shadow_score` **before** the first cycle — it cannot be reconstructed later, and Hardening Velocity (§3.5) is undefined without it
2. Extract from the Shadow Report: test name, expected result, actual result, failure message
3. **Do NOT** share the sealed test source code with the Implementer
4. The Implementer fixes the implementation based on failure descriptions only
5. Re-run validation (§4.3)
6. Repeat up to a configured maximum number of cycles
7. If Shadow Score remains > 0% after max cycles, escalate to human review

**Rationale:** Sharing only failure messages (not test code) forces the Implementer to fix the *root cause* rather than pattern-match against specific test assertions.

#### 4.4.1 Progressive Disclosure

Implementations MAY define disclosure levels that increase across hardening cycles. No level may include sealed test **source**.

| Level | Discloses | Notes |
|-------|-----------|-------|
| `failure_messages` | Test name, expected, actual, message | Default. The v1.0.0 behaviour. |
| `assertions` | The above, plus the text of the failing assertion | MAY be used at the final cycle only |

Disclosure escalation converts an unbounded guess into a solvable problem when an Implementer has stalled, without revealing the test body that would enable pattern-matching. The disclosure level reached MUST be recorded in the report.

#### 4.4.2 Escalation independence

If an implementation escalates by changing the Implementer's model between cycles, the replacement MUST NOT belong to a Seal Author's family (§4.2.1). Escalating into the Seal Author's family reproduces teach-to-test through model correlation rather than through visibility — the exact failure §3.6 exists to prevent.

**A flat hardening velocity across cycles is itself a signal.** An Implementer that fails the same test for a *different reason* each cycle is guessing, not converging, and the defect is more likely in the specification than in the code.

### 4.5 Tamper Evidence

To ensure sealed tests are not modified after generation:

1. After seal generation, compute: `hash = SHA-256(sorted_file_contents_of_sealed_directory)`
2. Store the hash in a tamper-evident log (e.g., state file, database, version control)
3. Before validation, recompute the hash and compare
4. If hashes differ, the Shadow Score is **invalid** — sealed tests were tampered with

**Recommended implementation:**
```bash
find <sealed_dir> -type f | sort | xargs shasum -a 256 | shasum -a 256
```

Implementations SHOULD additionally place a **canary** file inside the sealed directory whose access time is recorded at seal generation. A change in its access time before validation indicates the seal was read, not merely that it was unmodified — a hash detects tampering, but not reconnaissance.

### 4.6 Seal Plurality

Implementations MAY generate `N > 1` sealed suites, each authored **independently** from the same specification by a different model family. The suites are then merged into a single envelope for validation.

Plurality answers a question a single suite structurally cannot:

> One sealed suite tells you whether the **implementation** is right.
> Two independent sealed suites tell you whether the **specification** is right.

#### 4.6.1 Contradiction vs Divergence

|  | Definition | Counts toward Spec Ambiguity |
|---|-----------|------------------------------|
| **Contradiction** | Two suites assert on the same behaviour, incompatibly | ✅ Yes |
| **Divergence** | One suite tests a behaviour the other did not | ❌ No |

Divergence is the expected, desirable result of two authors with different instincts, and is the coverage dividend that motivates plurality. Only a **contradiction** demonstrates ambiguity: both authors read the same words and reached opposite conclusions about required behaviour.

#### 4.6.2 Spec Ambiguity

```
spec_ambiguity = contradicting_acceptance_criteria / total_acceptance_criteria
```

This is a measure of **specification quality**, not test quality. A high value means the specification supports materially different implementations — the code will be correct against one reading and wrong against another, and no Shadow Score can tell you which.

Implementations MAY gate on this value and halt before implementation begins. Detecting an ambiguous requirement before code exists is strictly cheaper than detecting it through a failing sealed test afterwards.

#### 4.6.3 Disclosure boundary

Any ambiguity report shared with the Implementer MUST describe disputed **behaviours** only. It MUST NOT contain test source, test names, assertion values, fixtures, or per-criterion test counts. Leaking the suite through the ambiguity report breaks the envelope as surely as leaking it directly.

---

## 5. Reporting Format

### 5.1 Shadow Report Structure

Implementations SHOULD produce a Shadow Report in at least one of these formats:

#### JSON Format (machine-readable)

```json
{
  "shadow_score_spec_version": "2.0.0",
  "report": {
    "id": "run-20260224-1200",
    "timestamp": "2026-02-24T12:00:00Z",
    "specification": "PRD.md",
    "shadow_score": 11.1,
    "level": "minor",
    "conformance_level": 4,
    "independence": "strong",
    "implementer_family": "anthropic",
    "seal_author_families": ["openai", "google"],
    "workspace_isolation": "strict",
    "spec_ambiguity": 0.0,
    "sealed_hash": "sha256:a1b2c3d4...",
    "seal_broken": false
  },
  "sealed_tests": {
    "total": 18,
    "passed": 16,
    "failed": 2
  },
  "open_tests": {
    "total": 12,
    "passed": 12,
    "failed": 0
  },
  "failures": [
    {
      "test_name": "test_rejects_gpl_dependency",
      "category": "security",
      "expected": "CLI exits with code 2",
      "actual": "CLI exits with code 0",
      "message": "GPL dependency not blocked"
    },
    {
      "test_name": "test_csv_report_includes_risk",
      "category": "edge_case",
      "expected": "CSV contains risk column",
      "actual": "Column missing",
      "message": "Report missing risk metadata"
    }
  ],
  "coverage_comparison": {
    "happy_path": { "open": 6, "sealed": 6, "delta": 0 },
    "edge_cases": { "open": 3, "sealed": 5, "delta": 2 },
    "error_handling": { "open": 3, "sealed": 4, "delta": 1 },
    "security": { "open": 0, "sealed": 3, "delta": 3 }
  },
  "hardening": {
    "cycles_completed": 1,
    "max_cycles": 3,
    "initial_shadow_score": 22.2,
    "final_shadow_score": 11.1
  }
}
```

#### Markdown Format (human-readable)

See `examples/` for complete rendered examples.

### 5.2 Required Fields

Field names below are **full JSON paths from the document root**. Fields under `report.*` describe the run; the root holds the envelope. Implementations MUST place fields at the stated path — a provenance field written at the wrong depth is not present, and a conformance claim that depends on it will silently fail to be enforced.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `shadow_score_spec_version` | string | ✅ | Spec version this report conforms to |
| `report.shadow_score` | number | ✅ | The computed Shadow Score (0–100) |
| `report.level` | string | ✅ | One of: `perfect`, `minor`, `moderate`, `significant`, `critical` |
| `sealed_tests.total` | integer | ✅ | Total sealed tests run |
| `sealed_tests.passed` | integer | ✅ | Sealed tests that passed |
| `sealed_tests.failed` | integer | ✅ | Sealed tests that failed |
| `failures` | array | ✅ | List of failure objects (test_name, expected, actual, message) |
| `report.independence` | string | ✅ at Level 4 | `strong` or `weak` (§3.6.1) |
| `report.seal_author_families` | array | ✅ at Level 4 | Model families that authored the sealed suites |
| `report.implementer_family` | string | ✅ at Level 4 | Model family that authored the implementation |
| `report.conformance_level` | integer | RECOMMENDED | Highest level claimed (1–4) |
| `report.advisory` | boolean | ✅ if `true` | Set when the score is not authoritative (§5.4) |
| `report.advisory_reason` | string | ✅ if `advisory` | Why the score is not authoritative |
| `report.sealed_hash` | string | RECOMMENDED | SHA-256 hash of sealed test directory |
| `report.seal_broken` | boolean | RECOMMENDED | True if tamper evidence or a canary indicates the seal was read or modified |
| `report.workspace_isolation` | string | RECOMMENDED | `strict` (disposable workspace) or `legacy` (§4.3) |
| `report.seal_author_models` | array | RECOMMENDED | Specific models that authored the sealed suites |
| `report.implementer_model` | string | RECOMMENDED | Specific model that authored the implementation |
| `report.spec_ambiguity` | number | ✅ if plurality used | Contradiction ratio (§4.6.2) |
| `hardening.initial_shadow_score` | number | ✅ at Level 3 | Score before the first hardening cycle |
| `hardening.cycles_completed` | integer | ✅ at Level 3 | Number of hardening cycles run |
| `hardening.hardening_velocity` | number | ✅ at Level 3 | Points recovered per cycle (§3.5) |
| `hardening.max_reveal` | string | RECOMMENDED | Highest disclosure level reached (§4.4.1) |
| `open_tests.*` | object | RECOMMENDED | Open test results for comparison |
| `coverage_comparison` | object | OPTIONAL | Category-level breakdown |

Implementations MAY add fields not listed here. They MUST NOT rename a listed field, and MUST NOT emit `report.seal_families` — an early spelling of `report.seal_author_families` that the reference schema rejects, because a validator that silently ignores an unrecognised provenance field will report a Level 4 claim it never actually checked.

**Provenance is not optional metadata.** A Shadow Score without `independence` and family provenance cannot be interpreted: 0% under `strong` independence and 0% under `weak` independence are different claims about the world, and only one of them is evidence.

### 5.3 Failure Categories

Implementations SHOULD categorize each sealed test into one of:

| Category | Description |
|----------|-------------|
| `happy_path` | Standard expected-input → expected-output scenarios |
| `edge_case` | Boundary conditions, empty inputs, max values, unicode |
| `error_handling` | Invalid inputs, missing data, malformed requests |
| `security` | Injection, overflow, unauthorized access, data leakage |

### 5.4 Advisory Reports

A Shadow Score MUST be marked `advisory: true` when any of the following holds:

| Condition | Reason |
|-----------|--------|
| `independence: weak` | Correlated blind spots bias the score toward 0% (§3.6) |
| `seal_broken: true` | The seal was read or modified; the score is unfalsifiable |
| The specification was truncated or summarised before reaching the Seal Author or Implementer | The score measures the summariser, not the implementation |
| Any sealed suite failed to execute | A suite that did not run is not a suite that passed |

Advisory reports MUST carry `advisory_reason` and MUST NOT be presented as a conformant Shadow Score in comparisons, badges, or dashboards.

An honest "this could not be measured" is more useful than a confident wrong number. A 0% advisory score is precisely the case that looks best and means least.

---

## 6. Conformance Levels

Implementations may claim conformance at four levels. Each level includes all requirements of the levels below it.

### Level 1 — Shadow Score Computation
**Requirements:**
- Computes Shadow Score using the formula in §3.3
- Produces a Shadow Report with all required fields (§5.2)
- Uses the interpretation scale in §3.4

**Does NOT require:** Sealed-envelope isolation (tests may be authored with knowledge of the implementation).

**Use case:** Retrofitting Shadow Score onto existing test suites for comparative analysis.

### Level 2 — Sealed-Envelope Isolation
**Requirements:**
- All of Level 1
- Sealed tests are generated before implementation begins
- Information isolation (§4.2) is enforced at context-isolation level or stronger
- Tamper evidence hash is computed and stored (§4.5)

**Use case:** AI agent pipelines and multi-agent build systems.

### Level 3 — Full Protocol with Hardening
**Requirements:**
- All of Level 2
- Hardening loop (§4.4) is implemented
- Failure messages shared with Implementer do NOT include test source code
- `initial_shadow_score` is recorded before the first cycle and hardening velocity is reported (§3.5)
- Shadow Score is recomputed after each hardening cycle

**Use case:** Production-grade autonomous build systems.

### Level 4 — Adversarial Independence
**Requirements:**
- All of Level 3
- Authorship independence (§4.2.1) is enforced **before dispatch**, not merely audited afterwards
- Seal Author and Implementer are of different model families; a violation aborts the run or forces `advisory: true`
- Validation uses a disposable verification workspace (§4.3) — sealed tests never enter the Implementer's workspace
- Hardening escalation never moves the Implementer into a Seal Author's family (§4.4.2)
- `independence`, `seal_author_families`, and `implementer_family` are reported (§5.2)
- Advisory conditions (§5.4) are detected and reported

**Seal plurality (§4.6) is RECOMMENDED but not required at Level 4.** Implementations using it MUST report `spec_ambiguity`.

**Use case:** Systems whose Shadow Scores are published, compared across tools, or used as a merge gate.

**Rationale:** Levels 1–3 progressively harden *information* isolation. They are all silently defeated by a single configuration choice — pointing the Seal Author and the Implementer at the same model. Level 4 closes the only remaining channel through which an implementation can be graded by a mind that shares its blind spots.

---

## 7. Reference Implementations

The reference implementation of the Shadow Score Specification is **[Dark Factory](https://github.com/DUBSOpenHub/dark-factory)**, an autonomous agentic build system for the GitHub Copilot CLI.

Dark Factory implements **Level 4** conformance:
- Sealed tests generated by QA Sealed agents from PRD only, from ≥ 2 model families (§4.1, §4.6)
- Cross-family invariants enforced at Phase 0 with abort-on-violation, and re-checked in CI (§4.2.1)
- Context-isolated agents via separate `task()` invocations, with the seal vault stored outside the repository (§4.2)
- Validation in a disposable worktree built from the Implementer's commit (§4.3)
- Multi-turn hardening with progressive disclosure capped at assertions (§4.4.1) and family-aware escalation (§4.4.2)
- SHA-256 hash plus canary stored in state.json (§4.5)
- Spec ambiguity gate before implementation begins (§4.6.2)
- `SHADOW-REPORT.json` carrying independence provenance and hardening velocity (§5.2)

The reference **Level 2** implementation is **[Terminal Stampede](https://github.com/DUBSOpenHub/terminal-stampede)**, a parallel agent runtime for CLI coding agents.

Terminal Stampede implements **Level 2** conformance:
- Sealed tests generated before agents launch, stored in `sealed-tests/` (§4.1)
- Information isolation — agents never see sealed tests or know they're being scored (§4.2)
- Merger agent runs both suites and integrates Shadow Score into merge report (§4.3)
- SHA-256 tamper hash verified via `.seal-hash` before validation (§4.5)

Lightweight reference validators for computing Shadow Score from test output are available in the [`validators/`](./validators/) directory.

---

## Appendix A: Worked Examples

### A.1 — Perfect Score (0%)

**Scenario:** Build a Fibonacci calculator CLI.

| Suite | Total | Passed | Failed |
|-------|-------|--------|--------|
| Sealed | 5 | 5 | 0 |
| Open | 8 | 8 | 0 |

**Shadow Score:** `0 / 5 × 100 = 0%` ✅ Perfect

The Implementer's tests covered all scenarios the sealed tests checked, plus 3 additional cases. This indicates thorough understanding of the specification.

### A.2 — Minor Gaps (11.1%)

**Scenario:** Build a license scanner CLI tool.

| Suite | Total | Passed | Failed |
|-------|-------|--------|--------|
| Sealed | 18 | 16 | 2 |
| Open | 12 | 12 | 0 |

**Shadow Score:** `2 / 18 × 100 = 11.1%` 🟢 Minor

**Failures:**
1. `test_rejects_gpl_dependency` — GPL dependency not blocked (security gap)
2. `test_csv_report_includes_risk` — Report missing risk column (edge case)

The Implementer built solid core functionality but missed a security edge case and a reporting detail. One hardening cycle resolved both.

### A.3 — Critical Gaps (60%)

**Scenario:** Build a user registration API.

| Suite | Total | Passed | Failed |
|-------|-------|--------|--------|
| Sealed | 15 | 6 | 9 |
| Open | 4 | 4 | 0 |

**Shadow Score:** `9 / 15 × 100 = 60%` 🔴 Critical

The Implementer wrote only 4 tests — all happy path. Sealed tests caught: missing email validation, no password hashing, duplicate user returns 500 instead of 409, SQL injection vulnerability, missing rate limiting, and more. This indicates the Implementer built to the "golden path" without considering real-world edge cases.

**Recommendation:** Re-implement with explicit attention to error handling and security requirements.

---

## Appendix B: FAQ

**Q: Can I use Shadow Score without AI agents?**  
A: Yes. Shadow Score works with any workflow where one party writes specification-based tests and another party implements the code. Human teams can use it for code review, pair programming assessment, or contractor evaluation.

**Q: What if the sealed tests themselves are wrong?**  
A: Sealed tests should be reviewed by a human (or a separate validator) before being finalized. Buggy sealed tests inflate the Shadow Score incorrectly. The tamper evidence hash (§4.5) ensures they aren't changed after the fact — but it doesn't guarantee correctness.

**Q: Does a 0% Shadow Score mean the code is perfect?**  
A: No. It means the code passes all sealed tests. The sealed tests may not cover every possible scenario. Shadow Score measures *specification compliance*, not *absolute correctness*.

**Q: How many sealed tests should I write?**  
A: Enough to cover every acceptance criterion in the specification, including happy path, edge cases, error handling, and security. As a guideline: 3–5 sealed tests per acceptance criterion.

**Q: Can the Implementer game the system?**  
A: If information isolation (§4.2) is properly enforced, it cannot game the system *deliberately*. It can still be advantaged accidentally — see the next question.

**Q: Why does it matter which model writes the sealed tests?**  
A: Because isolation only stops the Implementer from *seeing* the tests. It does not stop it from *thinking like* the author. Two instances of the same model family share failure modes: if the family doesn't think to test a scenario, it also doesn't think to handle it, so the sealed test is never written and the defect is never caught. The score reads 0% and the bug ships. Crucially, this bias is directional — it always pushes toward 0%, so a same-family pipeline systematically overclaims quality (§3.6).

**Q: Isn't requiring multiple model families expensive and restrictive?**  
A: It costs one configuration change, and only two roles are actually constrained (§3.6.2). Sharing a model between the Specifier and the Seal Author biases the score *upward*, which is conservative and permitted with disclosure. Only the pairings that hide defects are forbidden. If you genuinely have access to one family only, set `advisory: true` and report the score as non-authoritative rather than claiming Level 4.

**Q: What does seal plurality buy me over one good suite?**  
A: The ability to grade your *specification*. A single suite can only tell you whether the code matches that suite's reading of the spec. Two independent suites that contradict each other prove the spec supports two different systems — a defect no amount of implementation effort can fix, found before any code is written (§4.6).

**Q: Why did v2.0 stop copying sealed tests into the implementation workspace?**  
A: Because hardening re-invokes the Implementer *after* validation. Under the v1.0.0 procedure the sealed tests are, by cycle 2, sitting in a directory the Implementer can read — and agents with unscoped shell tools are limited by what they *can* do, not by what the prompt asked them not to do. v2.0 validates in a disposable workspace built from the Implementer's commit (§4.3).

**Q: How does Shadow Score compare to code coverage?**  
A: Code coverage measures *lines of code executed by tests*. Shadow Score measures *specification requirements satisfied by the implementation*. You can have 100% code coverage and a 50% Shadow Score (the code runs but produces wrong results for half the requirements).

**Q: Is Shadow Score useful for non-AI development?**  
A: Yes. Any team practicing independent verification and validation (IV&V) can benefit. The concept originates from quality engineering practices used in aerospace, medical devices, and safety-critical systems. Authorship independence (§3.6) has a direct human analogue: don't let the author of a module write its acceptance tests, and don't let their closest collaborator do it either.

---

## Appendix C: Changelog

### 2.0.0 (2026-07-28)

**Added**
- §3.6 Authorship Independence — independence classes (`strong` / `weak`) and the bias-direction table
- §4.2.1 Authorship Independence enforcement requirements
- §4.4.1 Progressive Disclosure — bounded escalation that never reveals test source
- §4.4.2 Escalation independence — model escalation may not enter a Seal Author's family
- §4.6 Seal Plurality — contradiction vs divergence, and the Spec Ambiguity metric
- §5.4 Advisory Reports — when a score MUST be marked non-authoritative
- **Level 4 — Adversarial Independence** conformance level
- Canary-based seal reconnaissance detection (§4.5)
- Report fields: `independence`, `seal_author_families`, `implementer_family`, `conformance_level`, `advisory`, `advisory_reason`, `seal_broken`, `workspace_isolation`, `spec_ambiguity`, `hardening.hardening_velocity`, `hardening.max_reveal`, `seal_author_models`, `implementer_model`

**Changed**
- §5.2 field names are now given as **full JSON paths**. v1.0.0 mixed dotted paths (`sealed_tests.total`) with bare names (`shadow_score`), leaving it ambiguous whether a field belonged at the root or under `report`. The reference implementation drifted on exactly this, and the resulting report still validated — the misplaced field was invisible to the Level 4 conditional, so the conformance claim passed unchecked. The reference schema now rejects misplaced provenance and the superseded `seal_families` spelling by name.
- A schema that silently ignores an unrecognised provenance field will report a conformance level it never verified. Provenance fields are therefore rejected on misspelling, not skipped.
- §5.4 advisory conditions are now machine-enforced: `independence: weak` and `seal_broken: true` require `advisory: true` with a reason.
- §4.3 validation now uses a **disposable verification workspace**; the v1.0.0 copy-in procedure is retained as `workspace_isolation: "legacy"` for single-shot validators
- §3.5 Hardening Velocity given an explicit formula; §4.4 requires recording `initial_shadow_score` before cycle 1, which Level 3 previously required but left uncomputable
- §4.2 isolation mechanisms now rank **topological** isolation above process isolation, with a note that context isolation is insufficient for agents holding unscoped filesystem tools
- §5.2 required fields are now scoped by conformance level
- "Gap Report" renamed to "Shadow Report" throughout, completing the `gap-score` → `shadow-score` rename

### 1.0.0 (2026-02-24)
- Initial specification release
- Shadow Score formula and interpretation scale
- Sealed-Envelope Protocol (4 phases)
- Reporting format (JSON + Markdown)
- Three conformance levels
- Reference implementation: Dark Factory