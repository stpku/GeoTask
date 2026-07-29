# GeoTask Control Evaluation Result v1.0

Status: implemented public contract  
Result schema version: `1.0`  
JSON Schema: [`schemas/geotask-control-evaluation-v1.0.schema.json`](../../schemas/geotask-control-evaluation-v1.0.schema.json)

## 1. Purpose

The Control Extension Profile defines decision rules, evidence recovery conditions, and task gates. The Control Expression Language makes those conditions safe to parse and evaluate. The Control Evaluation Result binds these pieces together without turning a condition check into an action executor.

The public evaluation layer answers:

- which assertion values and explicit domain values were used;
- whether each control expression evaluated to `true`, `false`, or `unknown`;
- which identifiers remain unknown;
- which outputs remain blocked;
- which outputs would be eligible for release if a caller separately authorizes them;
- which action and controls are declared by the task gate;
- whether any action was executed.

The answer to the last question is always `false` in this public contract.

## 2. Public API

```python
from geotask_core import (
    build_control_context,
    evaluate_control_profile,
)

execution_result = execute_canonical(document)

control_result = evaluate_control_profile(
    document,
    execution_result,
    domain_state={
        "ground_zone_clear": False,
        "clearance_evidence_age_seconds": 8,
    },
)

payload = control_result.to_dict()
```

`evaluate_control_profile()` is an explicit call. `execute_canonical()` does not automatically call it, change blocked outputs, or execute `next_action`.

### 2.1 CLI

The public CLI exposes the same observational contract:

```bash
geotask control evaluate task.yaml \
  --result execution-result.json \
  --state control-state.yaml
```

`execution-result.json` MUST use the canonical wrapper produced by
`GeotaskResult.to_dict()`. It can be generated directly with:

```bash
geotask run task.yaml --format v1-json --output execution-result.json
```

The optional state file may be JSON or YAML. The command emits Control
Evaluation Result JSON to stdout by default; `--output` writes the payload to a
file and `--compact` selects single-line JSON.

The CLI does not run the GeoTask document, execute `next_action`, change the
input result, or authorize any output. It rejects malformed result shapes,
cross-task result files, undeclared assertion checks, non-mapping state files,
and non-finite JSON values.

A serialized result can be validated independently:

```bash
geotask control validate control-evaluation.json
geotask control validate control-evaluation.json --format json
```

The command uses `load_control_evaluation()` to enforce this Schema and the
cross-field invariants described in this specification. It does not evaluate
expressions or rerun the source GeoTask. Execution-result and control-result
validation share the [Versioned Payload Validation v1.0](geotask-versioned-payload-validation-v1.0.md)
framework while retaining separate strict loaders.

## 3. Read-only `control_context`

`build_control_context()` creates an immutable context from two sources.

### 3.1 Assertion results

Each `CheckResult.assertion_id` becomes a direct expression identifier whose value is `CheckResult.value`.

```text
route_intersects_zone → true
altitude_conflict     → true
temporal_conflict     → unknown
```

The context also records provenance for each assertion value:

- assertion status;
- assurance level;
- deterministic flag;
- evidence references.

An assertion value is not promoted to a stronger assurance level by control evaluation. The evaluation layer reads the existing result and preserves its provenance.

### 3.2 Explicit domain state

The caller may provide a mapping of finite scalar values or nested mappings:

```python
{
    "vehicle": {
        "clearance": 4.0,
        "ready": True,
    },
    "review_complete": False,
}
```

The expression `vehicle.clearance >= 3` resolves by dotted mapping traversal.

Domain-state leaves may be:

- boolean;
- finite integer or decimal number;
- string;
- null, which represents `unknown`.

Lists, arbitrary objects, `NaN`, and infinity are rejected.

### 3.3 Collision rules

Explicit domain state cannot override an assertion ID. A collision is rejected rather than silently selecting one source.

The top-level key `assertions` is reserved. Domain mapping keys use identifier segments and should express hierarchy through nested mappings rather than embedding dots in one key.

The original caller mapping is copied and recursively frozen. Later mutation of the caller's object does not change the control context.

## 4. Expression evaluation

For a validated `geotask.control/1.0` document, the evaluator processes these blocks in stable order:

1. `decision_rule.expression`
2. `evidence_request.resume_when`
3. `evidence_conflict.resume_when`
4. `task_gate.resume_when`

Before evaluation, the same public Profile validator used by `validate_canonical()` is applied. Unsupported or malformed profiles return structured diagnostics and are not evaluated. The execution result must have the same `task_id` as the canonical document, and every `CheckResult.assertion_id` must be declared by that document; mismatches are rejected rather than evaluated.

Each block result includes:

```text
block
expression_field
expression
value
state
referenced_identifiers
unknown_identifiers
blocked_outputs
eligible_outputs
selected_action
next_action
required_controls
rejected_actions
declared_status
evaluation_error
action_executed
```

## 5. State semantics

### 5.1 Decision rule

A `decision_rule` does not by itself become a gate.

| Value | Block state |
|---|---|
| `true` | `satisfied` |
| `false` | `not_satisfied` |
| `unknown` | `unknown` |
| evaluation error | `error` |

For a result containing only a decision rule, `gate_satisfied` is null.

### 5.2 Blocking controls

`evidence_request`, `evidence_conflict`, and `task_gate` are blocking controls.

| `resume_when` value | Block state | Declared blocked outputs |
|---|---|---|
| `true` | `satisfied` | moved to `eligible_outputs` |
| `false` | `blocked` | remain in `blocked_outputs` |
| `unknown` | `unknown` | remain in `blocked_outputs` |
| evaluation error | `error` | remain in `blocked_outputs` |

Only `true` satisfies a gate. `false`, `unknown`, and evaluation errors are conservative and do not make an output eligible.

### 5.3 Aggregate state

For multiple blocking controls:

- any evaluation error makes the aggregate state `error`;
- otherwise any `false` condition makes it `blocked`;
- otherwise any `unknown` condition makes it `unknown`;
- only all-`true` blocking conditions make it `satisfied`.

`blocked_outputs` is the union of outputs still blocked by any control. An output cannot simultaneously appear in `eligible_outputs` if another control still blocks it.

## 6. `eligible_outputs` is not execution

`eligible_outputs` means only:

> Every evaluated blocking condition that names this output is currently satisfied.

It does not mean that:

- the executor changed an output contract;
- an approval was granted;
- a command was sent;
- a payload was released;
- a route was authorized;
- `next_action` ran.

Both the overall result and every block result contain:

```json
"action_executed": false
```

The public JSON Schema fixes this field to the constant `false`. A payload claiming `true` is schema-invalid.

## 7. Unknown identifiers

Every expression reports its referenced identifiers. An identifier is listed under `unknown_identifiers` when it is absent from the context or explicitly bound to null.

Example:

```text
route_intersects_zone = true
altitude_conflict     = true
temporal_conflict     = unknown
```

For:

```text
route_intersects_zone AND altitude_conflict AND temporal_conflict
```

The result is:

```text
value: unknown
unknown_identifiers: [temporal_conflict]
```

The evaluator does not replace missing evidence with `false`.

## 8. Serialization shape

A simplified result is:

```json
{
  "control_evaluation": {
    "schema_version": "1.0",
    "task_id": "gt19-uav-arrival-ground-clearance-release",
    "profile": {
      "id": "geotask.control",
      "version": "1.0"
    },
    "state": "blocked",
    "gate_satisfied": false,
    "control_context": {
      "values": {
        "ground_zone_clear": false,
        "clearance_evidence_age_seconds": 8
      },
      "entries": {
        "clearance_evidence_age_seconds": {
          "name": "clearance_evidence_age_seconds",
          "value": 8,
          "source": "domain_state",
          "assertion_status": "",
          "assurance_level": "",
          "deterministic": false,
          "evidence_refs": []
        },
        "ground_zone_clear": {
          "name": "ground_zone_clear",
          "value": false,
          "source": "domain_state",
          "assertion_status": "",
          "assurance_level": "",
          "deterministic": false,
          "evidence_refs": []
        }
      }
    },
    "evaluations": [
      {
        "block": "task_gate",
        "expression_field": "resume_when",
        "expression": "ground_zone_clear == true AND clearance_evidence_age_seconds <= 15",
        "value": false,
        "state": "blocked",
        "satisfied": false,
        "referenced_identifiers": [
          "clearance_evidence_age_seconds",
          "ground_zone_clear"
        ],
        "unknown_identifiers": [],
        "blocked_outputs": [
          "automatic_drop_authorization",
          "payload_release_command"
        ],
        "eligible_outputs": [],
        "selected_action": "hold_position_and_request_ground_clearance",
        "next_action": "request_ground_clearance_and_reverify",
        "required_controls": [
          "retain_live_ground_clearance_evidence",
          "reverify_clearance_before_release"
        ],
        "rejected_actions": [
          "release_cargo_because_over_target"
        ],
        "declared_status": "blocked_pending_ground_clearance",
        "evaluation_error": "",
        "action_executed": false
      }
    ],
    "unknown_identifiers": [],
    "blocked_outputs": [
      "automatic_drop_authorization",
      "payload_release_command"
    ],
    "eligible_outputs": [],
    "diagnostics": [],
    "action_executed": false
  }
}
```

The complete machine-readable shape is defined by the public JSON Schema.

## 9. Result immutability and side effects

Control evaluation does not mutate:

- the `CanonicalDocument`;
- the `GeotaskResult`;
- the caller's domain-state mapping;
- Core operator results;
- output contracts;
- assurance levels.

`ControlContext.values` and `ControlContext.entries` are recursively read-only mappings. `to_dict()` returns a detached serializable copy.

## 10. Trust boundary

Assertion values carry the provenance already present in `CheckResult`. Explicit domain state is supplied by the caller and is labelled `domain_state`; the evaluator does not independently verify its source.

A Runtime or Domain Pack may enforce stronger requirements, such as:

- accepted evidence authorities;
- freshness limits;
- signed state updates;
- human approval;
- command authorization;
- transactional output release.

Those responsibilities are outside the public evaluation layer. They must not be represented as completed merely because a finite expression evaluated to `true`.

## 11. Versioning

Incompatible changes to the serialized result require a new `CONTROL_EVALUATION_SCHEMA_VERSION` and a new JSON Schema file. Existing version `1.0` keeps `action_executed` fixed to `false` and preserves conservative handling of `unknown` and evaluation errors.
