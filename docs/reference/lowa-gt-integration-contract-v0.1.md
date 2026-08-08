# GeoTask ↔ Lowa-GT Integration Contract v0.1

**Status:** v0.1 shadow transport aligned with committed Lowa S1 exporter / read-only-first  
**Date:** 2026-08-07  
**Purpose:** define how GeoTask and Lowa-GT cooperate without creating a second low-altitude System of Record or implicit dual writes. The serialized S1→S2 transport is executable and tested; no production write-back or 50-site industry result is claimed yet.

## 1. System roles

### Lowa-GT

Lowa-GT remains the authoritative low-altitude business system. It owns real low-altitude business facts and workflows, including facility/site state, spatial context, evidence sources/items, current and historical assessments, decisions, resource state, evidence requests, human review tasks, reports and audit records.

### GeoTask

GeoTask acts as the trust-control layer. It consumes bounded task-level snapshots/references and returns deterministic verification, dependency/impact, evidence-gap and control artifacts.

GeoTask does not become the authoritative database for Lowa-GT facts.

## 2. Integration invariant

```text
Lowa-GT authoritative state
        ↓ read-only projection
Trusted State Snapshot / references
        ↓
GeoTask verification + impact + control
        ↓
VerificationResult / ImpactSet / ControlEvaluation / Artifact bundle
        ↓
Lowa-GT workflow decides whether to create review work,
rescore, refresh a report or perform any database write
```

There is no implicit write-back from GeoTask to Lowa-GT.

## 3. First integration slice

The first supported slice is deliberately narrow:

> After a single facility receives new evidence or an evidence bundle changes, determine which claims, assessment outputs and report sections are affected; state what remains unverifiable/conflicted; and determine whether a human-approved rescore or report refresh is eligible.

The first slice is not flight authorization, UTM, real-time flight control or a new low-altitude world-model database.

## 4. Lowa-GT → GeoTask input contract

Lowa-GT exports a bounded read-only projection for one integration task. In the v0.1 serialized shadow profile, Lowa's authoritative facility/resource entity is transported using its native `site` identifier; GeoTask must not rename that source identity into a second domain object. The current envelope is:

```yaml
integration_contract: lowa-gt/geotask-v0.1
snapshot_id: <stable opaque id derived from bounded source identity>
captured_at: <timezone-aware timestamp>
mode: shadow_read_only
subject:
  system: lowa-gt
  entity_type: site
  entity_id: <stable Lowa-GT site id>
business_projection:
  content: <SiteBusinessProjection serialized content>
  content_sha256: <canonical projection hash>
current_assessment:
  record_id: <optional current AssessmentRecord id>
  input_snapshot_sha256: <optional exact serialized-input hash>
  input_evidence_hash: <temporary legacy compatibility field; optional>
  input_binding: <optional lowa-assessment-input/v0.1 envelope; null for legacy records>
  source_quality: <authoritative_record|legacy_fallback|none>
current_evidence:
  evidence_hash: <native Lowa EvidenceBundle evidence hash>
  content_sha256: <serialized bundle hash>
  source_ref: <optional stable source reference used only for explicit dependency matching>
  item_count: <count>
  bundle: <bounded EvidenceBundle content>
current_decision:
  record_id: <optional current DecisionRecord id>
  evidence_hash: <optional DecisionRecord evidence hash>
  source_quality: <authoritative_record|resource_state_fallback|legacy_fallback|none>
open_evidence_requests: []
active_review_tasks: []
report_projection:
  persisted_current_report: false
  render_service: SiteDecisionReportService
  report_inputs_sha256: <bounded current report-input fingerprint>
side_effects:
  database_write_performed: false
  assessment_created: false
  decision_created: false
  evidence_request_created_or_closed: false
  review_task_created_or_closed: false
  report_published: false
```

The expanded v0.1 transport profile is intentionally source-shaped rather than a duplicated GeoTask World State database. GeoTask may materialize bounded verification artifacts from this snapshot, but Lowa-GT remains the only owner of the current business records.

### Assessment input-binding compatibility extension

The Integration verifier may accept an optional `current_assessment.input_binding` envelope with contract id `lowa-assessment-input/v0.1`. This is an **Integration compatibility gate**, not a GeoTask Core primitive and not evidence that Lowa currently persists the field. Until Lowa Product explicitly adopts the source contract, existing S1 records remain valid legacy inputs and continue to fail closed where exact provenance cannot be proven.

When the extension is present, Integration evaluates two questions separately:

1. **Input identity** — whether the AssessmentRecord declares an exact canonical input identity.
2. **Dependency relation** — whether the current changed source is explicitly declared as an assessment dependency.

For an `evidence_bundle` dependency, exact comparison requires both a stable `current_evidence.source_ref` and a matching dependency `ref`; only then may `content_sha256` be compared. Missing source references, missing dependency hashes or undeclared dependencies must never be repaired through site-id inference, timestamp proximity or the legacy `input_evidence_hash` field.

The supported dependency relation states are:

```text
matched
changed
not_declared
unverifiable
```

`not_declared` means GeoTask must **not** mark an assessment stale merely because the current EvidenceBundle changed. It does not mean the assessment is globally fresh against every possible upstream dependency.

### Required reference semantics

Every referenced object that can affect a decision must provide, directly or through a resolvable artifact:

- stable source-system identifier;
- version/revision when available;
- exact hash when the source supports immutable byte binding;
- timezone-aware capture/effective timestamp;
- validity/freshness metadata where relevant;
- explicit source-system ownership.

GeoTask must not invent a missing version, precedence or freshness policy.

## 5. Suggested semantic mapping

The mapping is conceptual and must not be implemented as database duplication.

| Lowa-GT business concept | GeoTask role |
|---|---|
| current business projection | bounded World State / State Snapshot input |
| evidence source | Evidence source/provenance reference |
| evidence item / evidence bundle | Evidence / Observation reference |
| assessment record | derived claim / assessment artifact reference |
| decision record | decision/output reference |
| evidence request | Evidence Request / missing-evidence requirement |
| review task | human review requirement / control prerequisite |
| audit record | provenance / audit reference |

## 6. GeoTask → Lowa-GT output contract

GeoTask returns a read-only result bundle. At minimum the bundle must be able to represent:

### VerificationResult

- which declared condition was checked;
- `satisfied`, `contradicted`, `unverifiable` or `conflicted` semantics;
- exact input/reference bindings;
- reasons and failure-closed state.

### ImpactSet

- affected claim/assessment/output/report targets;
- explicitly reused/unaffected targets where useful;
- no automatic scope expansion beyond declared dependency information.

### EvidenceRequest

When additional evidence is required:

- reason;
- required fields/evidence class;
- affected/blocked outputs;
- resume condition.

### ControlEvaluation

At minimum distinguish:

```text
rescore_eligible
report_refresh_eligible
human_confirmation_required
production_write_performed = false
production_report_refreshed = false
action_executed = false
```

GeoTask returning `eligible=true` never proves that Lowa-GT performed the action.

### Optional HumanBaselineComparison

A study may compare an already valid shadow batch against serialized `lowa-human-review-baseline/v0.1` rows, but the comparison layer must not create or infer Lowa ground truth.

For a normalized historical outcome to enter an agreement denominator, the baseline row must provide an explicit Lowa-owned mapping rule and `mapping_confidence=exact`. `unknown`, missing, temporally incompatible, or Integration-ambiguous rows remain coverage evidence but are excluded from exact outcome agreement.

Integration may derive only bounded comparison classes from its own already-declared result fields. In particular, a generic `request_review` caused by missing provenance, pointer conflict or another trust uncertainty must remain comparison `unknown`; it cannot be relabelled as proof that Lowa required human approval.

Every baseline study must declare one temporal mode:

```text
prospective_same-time
retrospective_latest-known
retrospective-fixed-cutoff
```

The comparison artifact remains read-only and must explicitly preserve zero database access/write, zero LLM ground-truth inference, zero review-task mutation, zero report publication, and zero action authorization/execution.

## 7. Read-only-first and human-approved recalculation

The v0.1 integration is read-only by default.

GeoTask must not directly:

- create or update Lowa-GT database records;
- overwrite an assessment;
- refresh a report;
- close a review task;
- promote a resource state;
- publish a recommendation;
- trigger a real-world action.

If GeoTask determines that a rescore or report refresh is required/eligible, Lowa-GT remains responsible for presenting the reason, obtaining any required explicit confirmation, performing the operation through its own service boundary and creating the new authoritative record.

The resulting new authoritative state may then be projected back to GeoTask for reverification.

## 8. No dual-write rule

No field may be treated as simultaneously authoritative in GeoTask and Lowa-GT.

GeoTask artifacts may cache or bind a snapshot/reference for replay, but such artifacts are evidence of what a verification run used, not a competing current business record.

## 9. Version and hash behavior

1. Stable source IDs identify business entities/records; hashes identify exact immutable content when available.
2. A changed evidence-bundle hash must be treated as a potential dependency change, not as proof that every downstream conclusion is invalid.
3. Missing historical hashes/versions remain explicit legacy unverifiability; they must not be silently reconstructed.
4. Timestamp comparison alone is insufficient to prove full input equivalence when the source system has not persisted complete input fingerprints.
5. Integration-contract version changes must be explicit and backward compatibility documented.

## 10. Failure-closed rules

GeoTask must fail closed when:

- the referenced entity cannot be unambiguously identified;
- a required authoritative reference is missing;
- a required version/hash binding cannot be verified;
- evidence freshness cannot be established when freshness is required;
- two valid sources conflict without an explicit policy;
- a requested impact/recompute operation exceeds the declared bounded scope;
- an operation would require a Lowa-GT write that has not been explicitly approved through Lowa-GT.

## 11. First shadow-mode acceptance criteria

Before any suggestion mode or write-enabled workflow is considered, a shadow integration must demonstrate:

1. zero unauthorized Lowa-GT database writes;
2. deterministic replay for the same snapshot/artifact bundle;
3. traceability from every configured conclusion to source, time and relevant version/hash;
4. bounded impact that does not expand to unrelated facilities or unrelated report sections;
5. understandable human explanation of what changed, why reevaluation is required and what remains missing;
6. a measurable comparison against current human review baseline on a declared sample.

## 12. Explicit Cross-Line Promotion Gate

A capability proven inside Lowa-GT does not automatically become GeoTask Core. The three lines remain independent:

- **Lowa Product:** owns low-altitude business facts, authoritative records, product workflows and real writes/actions;
- **Lowa-GT Integration:** validates whether Core capabilities and candidate abstractions work against Lowa-shaped reality;
- **GeoTask Core:** owns industry-neutral reusable contracts and deterministic semantics.

Integration validation produces evidence for a **Promotion Candidate**; it is not itself a transfer of capability ownership. Any cross-line ownership transfer requires the explicit [`Cross-Line Promotion Gate v0.1`](cross-line-promotion-gate-v0.1.md) and a recorded `PROMOTE`, `KEEP_LOCAL`, `DEFER` or `REJECT` outcome.

An abstraction is considered for Core only after the Gate also establishes:

- it is expressed without low-altitude-specific business semantics;
- it is independently useful in at least one second industry/system;
- it preserves Core's deterministic, fail-closed and replayable constraints;
- it does not require GeoTask to become the domain System of Record;
- it has Core-native public-safe verification with no live Lowa dependency;
- public naming/version/migration impact is explicit.

Using an already-released Core contract inside Integration is ordinary dependency consumption and does not require promotion because Core ownership does not change.

## 13. Deferred items

v0.1 intentionally defers:

- production write-back automation;
- flight mission authorization;
- live airspace/aircraft/UTM integration;
- public Lowa-GT Marketplace;
- multi-tenant billing;
- third-party pack certification claims;
- creation of a second low-altitude business database inside GeoTask.

## 14. Strategic outcome

The integration succeeds when the two systems strengthen each other without collapsing their boundaries:

- Lowa-GT supplies real industry state, workflows and accountability;
- GeoTask supplies generic verification, bounded impact, uncertainty and control semantics;
- the integration proves a reusable Decision Assurance pattern rather than a one-off low-altitude code path.