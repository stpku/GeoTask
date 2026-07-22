# Security Policy

## Reporting a Vulnerability

GeoTask Core is a deterministic computation library. It contains no credentials,
secrets, API keys, or network connections. All results are produced by local
operators — no external services are called.

If you discover a security vulnerability, please **do not** open a public issue.

If GitHub private vulnerability reporting is enabled for this repository, use
the repository's Security page to submit the report privately:

**https://github.com/stpku/GeoTask/security**

If no private reporting option is visible, do not publish vulnerability details
in a public issue. Open a minimal issue requesting a private contact channel,
without including exploit details, sensitive inputs, or reproduction material.

## What We Care About

- Input handling that could cause unexpected behavior
- Integer overflow or floating-point edge cases in spatial operators
- YAML parsing vulnerabilities
- Information leakage through error messages or diagnostics
- Build or CI pipeline exposures

## What's Out of Scope

- Model-output verification errors (these are correctness issues, not security)
- Domain Pack or Runtime vulnerabilities (separate repositories)
- Deployment-specific configuration issues

## Determinism vs. Correctness

GeoTask Core guarantees **determinism**: the same input to the same version of a
registered operator always produces the same output. It does not claim mathematical
correctness in the formal proof sense. Results should be interpreted as:

> The result was produced by the repository's deterministic implementation for
> the declared input at the stated assurance level.

## Supported Versions

Only the `main` branch of the public repository is supported.

| Branch | Supported |
|--------|-----------|
| `main` | ✅ |
