"""v1.0 test suite organized by subsystem.

This directory provides a structured home for v1.0 tests as they are split
from the monolithic test_v1_foundation.py and test_v1_hardening.py files.

Current test files (tests/):
  - test_v1_foundation.py  — canonicalization, validation, execution, enums, IDs
  - test_v1_hardening.py   — CLI validation, on_error policies, output contract,
                              duplicate YAML keys, edge cases, result serialization

Planned split (future):
  - test_canonicalization.py
  - test_validation.py
  - test_execution.py
  - test_execution_policy.py
  - test_output_contract.py
  - test_assurance.py
  - test_operators.py
  - test_result_serialization.py
  - test_cli.py
"""
