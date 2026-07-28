# GeoTask Status and Assurance Model

GeoTask separates execution lifecycle, claim status, verification mode, provenance, and assurance level. These concepts answer different questions and MUST NOT be collapsed into one `status` field.

## 1. Five Separate Questions

| Question | Concept | Example |
|---|---|---|
| Did the execution step finish? | Execution status | `completed` |
| What happened to the proposition? | Claim status | `verified` |
| How was it checked? | Verification mode | `local_deterministic` |
| Who or what produced it? | Provenance | `model_generated` |
| How strong is the resulting confidence? | Assurance level | `model_local_agreement` |

A completed execution may still contain contradicted, unverifiable, or invalid claims.

## 2. Execution Status

The public v1 enum defines:

| Status | Meaning |
|---|---|
| `pending` | The step has not started. |
| `running` | The step is in progress. |
| `completed` | The planned execution finished. |
| `partial` | Some work completed, but the plan did not fully finish. |
| `failed` | The step failed. |
| `skipped` | The step was intentionally not executed. |

`completed` MUST NOT be interpreted as “all outputs are correct.” It only describes lifecycle completion.

## 3. Core Claim Status

The public `ClaimStatus` enum defines:

| Status | Meaning | Typical next action |
|---|---|---|
| `proposed` | A claim exists but has not been computed. | execute or review |
| `computed` | A value was produced but not yet verified. | verify |
| `verified` | The claim is supported by the declared verification path. | use subject to assurance |
| `contradicted` | A compared claim conflicts with the verified result. | reject or revise |
| `need_review` | A qualified reviewer is required. | request review |
| `need_data` | Required data is missing. | request evidence/data |
| `invalid_input` | The input is structurally or semantically invalid. | repair input |
| `invalid_operator` | The operator is unsupported or invalid. | choose registered operator |
| `invalid_reference` | An object or assertion reference cannot be resolved. | repair reference |
| `execution_error` | Execution failed unexpectedly. | retry, inspect, or fail |
| `unverifiable` | Current information cannot support verification. | request evidence or review |

### 3.1 Boolean Value Is Not Claim Status

A valid deterministic check may produce:

```text
value: false
status: verified
```

This means “the verified answer is false,” not “verification failed.”

Likewise:

```text
model_claim: true
local_value: false
status: contradicted
```

means the model claim disagrees with the local result.

## 4. Verification Mode

Defined modes:

| Mode | Meaning |
|---|---|
| `none` | No verification is requested. |
| `model_self_check` | The model reviews its own output. |
| `local_deterministic` | A local deterministic operator verifies the claim. |
| `model_local_compare` | Model output is compared with local execution. |
| `cross_model_compare` | Independent model results are compared. |
| `human_review` | A human reviewer verifies the result. |

Verification mode describes the process requested or completed. It does not automatically grant the highest possible assurance level.

## 5. Assurance Level

Assurance levels are ordered from weakest to strongest:

| Numeric level | Name | Minimum evidence |
|---:|---|---|
| 0 | `unverified` | No verification evidence. |
| 1 | `model_generated` | Produced by a model. |
| 2 | `model_self_checked` | Model generated and self-reviewed. |
| 3 | `local_deterministic` | Recomputed by a deterministic local operator. |
| 4 | `model_local_agreement` | Model result agrees with local deterministic result. |
| 5 | `independent_cross_verified` | Independently checked through another path. |
| 6 | `human_reviewed` | Reviewed by an authorized human under the relevant process. |

### 5.1 Assurance Is Not Probability

These values are ordinal process levels, not calibrated probabilities. `local_deterministic` does not mean “100% likely correct” if the input data or CRS is wrong. It means the declared deterministic computation was executed successfully on the supplied inputs.

### 5.2 No Self-Elevation

A model MUST NOT label its own output `local_deterministic`. A caller MUST NOT label a result `human_reviewed` merely because a human opened the page. The required process must actually occur and be recorded.

## 6. Provenance

Recommended provenance labels include:

- `model_generated`
- `local_deterministic`
- `connector_supplied`
- `externally_verified`
- `human_supplied`
- `human_reviewed`

Provenance answers where the value came from. Assurance answers how strongly it was verified.

Example:

```yaml
result:
  value: 5.0
  unit: meter
  status: verified
  provenance: local_deterministic
  assurance_level: local_deterministic
```

Compared model result:

```yaml
comparison:
  model_value: 5.0
  local_value: 5.0
  status: verified
  provenance:
    model: model_generated
    reference: local_deterministic
  assurance_level: model_local_agreement
```

## 7. Application Workflow States

GT examples use task-level states such as:

- `blocked`
- `conflicted`
- `coordinated`
- `reachable`
- `insufficient_margin`
- `insufficient_clearance`

These belong under `extensions` or a Domain Pack. They are not current Core `ClaimStatus` enum members.

Example:

```yaml
extensions:
  mission_gate:
    status: blocked
    reason: insufficient_range_after_required_reserve
```

A workflow state SHOULD include:

- a reason;
- affected or blocked outputs;
- the selected next action;
- a resume condition;
- an expected post-action state.

## 8. Recommended State Transitions

### 8.1 Deterministic Check

```text
proposed → computed → verified
                    ↘ execution_error
```

### 8.2 Model Comparison

```text
model_generated + local_deterministic
               → verified / contradicted
```

### 8.3 Missing Data

```text
proposed → need_data / unverifiable
         → evidence_request
         → data supplied
         → recompute
```

### 8.4 Conflicting Evidence

```text
source A verified
source B verified
A ≠ B
→ conflicted
→ conflict review
→ authoritative resolution
→ recompute
```

## 9. Anti-Patterns

### Anti-pattern: treating `false` as an error

Incorrect:

```text
value=false → failed
```

Correct:

```text
value=false, status=verified
```

### Anti-pattern: treating completion as correctness

Incorrect:

```text
execution=completed → all claims trusted
```

Correct: inspect each check and its assurance.

### Anti-pattern: allowing model provenance to claim local assurance

Incorrect:

```text
provenance=model_generated
assurance=local_deterministic
```

unless a separate local execution was actually performed.

### Anti-pattern: hiding unknown as false

Missing evidence is not equivalent to a verified false result.

## 10. Related Documents

- [Language and Execution Specification](../spec/geotask-language-spec-v1.0.md)
- [Evidence and Recovery](evidence-and-recovery.md)
- [White Paper](../whitepaper/GeoTask_White_Paper_v0.1.md)
- [GT01–GT15 Cookbook](../cookbook/gt01-gt15.md)
