# Contributing to GeoTask Core

**English** | [简体中文](CONTRIBUTING.zh-CN.md)

Thanks for your interest. GeoTask Core is a focused library for verifiable spatiotemporal task representation and deterministic verification. Keep the public Core lightweight, reproducible, and free of customer data, model credentials, private Runtime logic, and patent-sensitive implementation details.

## Dev setup

```bash
git clone https://github.com/stpku/GeoTask.git
cd GeoTask
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

The development extra installs `pytest`, `jsonschema`, and `matplotlib`. Python 3.10 is the minimum. The only runtime dependency is PyYAML.

## Running tests

```bash
pytest
pytest tests/ -v
pytest tests/ -x
pytest tests/test_documentation_system.py -q
```

Tests live in `tests/`. New operators must cover normal cases, edge cases, invalid input, and incompatible object types.

## Welcome contributions

- Parser, validation, execution, and result-assembly fixes
- Better structured diagnostics and error messages
- General-purpose deterministic operator proposals
- English or Chinese documentation improvements
- New robotics, UAV, autonomous-driving, GIS, or urban-governance cases
- JSON Schema and conformance-test improvements
- Mobile experience and accessibility fixes

## Code style

- No heavy runtime dependencies beyond PyYAML.
- Pure functions are preferred. Avoid class state unless it is a registry or dispatcher.
- Use dataclasses for data containers. `v1/ir.py` is the canonical example.
- Use enum members internally and convert to strings at serialization boundaries.
- Add type hints to public functions using Python 3.10+ syntax.
- Keep docstrings concise and factual.
- Do not add customer data, real credentials, API keys, or patent evidence.

## Architecture constraints

1. `ir.py` and `enums.py` are pure leaves.
2. `ops.py` is a pure math module with no I/O.
3. Core must not import private Runtime or Domain Pack implementation.
4. Validation must be deterministic.
5. Operators must return the same result for the same inputs.
6. Operator contracts must define compatible input types, output type, units, and boundary semantics.

## Pull request process

1. Open an issue first for substantial features or new operators.
2. Fork the repository and create a focused branch.
3. Write or update tests and documentation.
4. Run `pytest` and confirm that all tests pass.
5. Open a pull request against `main` with the problem, approach, test results, and boundary impact.

Small, coherent PRs are easier to review. A documentation translation, schema update, or complete weekly case may legitimately touch several files; keep one clear purpose rather than optimizing for an arbitrary file count.

## What belongs in Core

- Task format and Canonical IR
- Parsing and compatibility handling
- Structural and reference validation
- Deterministic operators
- Results, statuses, and assurance metadata
- CLI, JSON Schema, examples, and public conformance tests

## What does not belong in public Core

- Hosted model execution and API keys
- Production orchestration, model routing, and cost governance
- Industry-specific Domain Packs and customer thresholds
- Private data connectors and approval workflows
- Automatic control of real devices
- Unpublished patent-sensitive implementation details

When in doubt, open an issue describing the problem, general-purpose value, expected contract, and proposed boundary.

## New operator proposals

A Core operator should be cross-domain, deterministic, offline, type-safe, unit-aware, and backed by normal, boundary, and error tests. Do not add an operator only to make one demonstration convenient.

## New weekly cases

A public GT case should include a concrete application question, explicit objects and constraints, reusable Core assertions where available, differentiated candidate actions, a local verification path, a safe blocked or recovery state when needed, tests, and a real-world limitation statement.

See the [GT01–GT13 Cookbook](docs/cookbook/gt01-gt13.md) or [中文案例手册](docs/cookbook/gt01-gt13.zh-CN.md).

## Conduct and security

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). Do not report security vulnerabilities in a public issue; follow [SECURITY.md](SECURITY.md).
