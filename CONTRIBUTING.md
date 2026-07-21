# Contributing to GeoTask Core

Thanks for your interest. GeoTask Core is a focused library and we keep the scope tight: lightweight spatial task representation with deterministic verification. No heavy dependencies, no platform features.

## Dev Setup

```bash
git clone https://github.com/GeoTask/geotask-core.git
cd geotask-core
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

That installs the package in editable mode plus `pytest` and `matplotlib` for development.

Python 3.10 is the minimum. The only runtime dependency is PyYAML.

## Running Tests

```bash
pytest                          # all tests
pytest tests/ -v                # verbose
pytest tests/ -x                # stop on first failure
pytest tests/ --cov=geotask_core  # with coverage (install pytest-cov)
```

Tests live in `tests/`. Try to keep test files under 500 lines. Split large test suites into focused files in subdirectories.

## Code Style

- No dependencies beyond stdlib and PyYAML. Period.
- Pure functions preferred. Avoid class state unless it is a registry or dispatcher.
- Use dataclasses for data containers. `v1/ir.py` is the canonical example.
- Enum members, not raw strings. Convert to strings only at serialization boundaries (`to_dict()`, CLI output).
- Type hints on public functions. Python 3.10+ syntax (`list[str]`, `dict[str, int]`, `X | None`).
- Docstrings are concise. Describe what, not how. Skip redundant summaries that paraphrase the function name.
- No visual separator lines (`# ====`), no "defence in depth" or "hardened" language in comments.
- Function-internal imports are acceptable only for lazy loading to avoid import cycles. Prefer module-level imports.

## Architecture Constraints

These are enforced by review. Do not violate them.

1. **`ir.py` and `enums.py` import nothing from Core.** They are pure leaves.
2. **`ops.py` is a pure math module.** No imports from `geotask_core` at all.
3. **Core must not import from Runtime.** `geotask_core` never imports `geotask_runtime`.
4. **No circular dependencies.** The dependency graph flows inward from runner/cli to parser/canonicalizer/validator/executor to ir/enums/ops.
5. **Validation is deterministic.** The validator produces the same diagnostics for the same input every time.
6. **Operators are deterministic.** Every operator implementation must return the same result for the same inputs, with no I/O, no randomness, no external state.

## Pull Request Process

1. Open an issue first. Describe the problem or feature before writing code.
2. Fork and branch. Keep changes focused on one thing.
3. Write or update tests. New operators must have tests covering normal cases, edge cases, and error conditions.
4. Run `pytest` and confirm all tests pass.
5. Open a PR against `main`. Include a clear description and reference the issue.
6. Wait for review. A maintainer will check architecture constraints, test coverage, and code style.

Small PRs are reviewed faster. If your change touches more than 3 files, consider whether it can be split.

## What Belongs, What Doesn't

**Core scope:** format parsing, canonical IR, validation, deterministic operators, result assembly, CLI.

**Not Core:** LLM calling, model routing, task orchestration, domain-specific rules, data connectors, governance policies, benchmarks, audit trails. These belong in the Runtime layer or separate packages.

When in doubt: if it requires a network call or a heavy dependency, it probably does not belong in Core.

## Questions?

Open an issue on GitHub. We respond to questions about architecture, operator design, and contribution scope.
