# Contributing to Shadow Score Spec

Thank you for your interest in contributing to the Shadow Score Specification! This is an open specification and contributions are welcome.

## How to Contribute

### Spec Changes

The specification (`SPEC.md`) is the core artifact. Changes to the spec affect all conforming implementations.

1. **Open an issue first** to discuss the proposed change before submitting a PR
2. Explain the motivation and any impact on existing conformance levels
3. Include worked examples if the change affects the formula or protocol

### New Validators

Reference validators in additional languages are welcome. PRs for Go, Rust, TypeScript, and other languages are encouraged.

Requirements for new validators:
- Must conform to the current spec version
- Must handle the same input format as the existing validators (or document differences)
- Must produce output conforming to `validators/shadow-report-schema.json`
- Must include unit tests
- Must pass against all examples in `examples/`

### Adopter Listings

If you're using Shadow Score in your project, add it to the Adopters table in `README.md`:

1. Fork the repository
2. Add your project to the table with conformance level and description
3. Submit a PR

### Bug Reports

Found an inconsistency, typo, or bug in a validator? Open an issue with:
- What you expected
- What actually happened
- Steps to reproduce (if applicable)

## Development Setup

```bash
git clone https://github.com/DUBSOpenHub/shadow-score-spec.git
cd shadow-score-spec

# Run the validator unit tests
python -m pytest validators/test_shadow_score.py -v

# Run a validator against an example
python validators/shadow-score.py \
  --sealed examples/02-minor-gaps/sealed-results.json \
  --open examples/02-minor-gaps/open-results.json \
  --format summary
```

## Code of Conduct

Be respectful, constructive, and collaborative. We're building an open standard — thoughtful disagreement is welcome, personal attacks are not.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
