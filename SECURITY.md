# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in the Shadow Score reference validators or specification, please report it responsibly.

### How to Report

1. **Do not open a public issue** for security vulnerabilities
2. Email the maintainer at the address listed on the [GitHub profile](https://github.com/DUBSOpenHub)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Assessment**: Within 7 days
- **Fix**: Depends on severity, but we aim for prompt resolution

### Scope

This security policy covers:
- **Reference validators** (`validators/shadow-score.py`, `validators/shadow-score.sh`) — e.g., input injection, path traversal
- **JSON Schema** (`validators/shadow-report-schema.json`) — e.g., schema bypass enabling malicious payloads
- **Specification** (`SPEC.md`) — e.g., protocol weaknesses that could allow gaming the Shadow Score

### Out of Scope

- Implementations of the spec by third parties (report to those projects directly)
- Sealed test quality (this is a correctness concern, not a security concern)

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.0   | ✅ Yes    |
