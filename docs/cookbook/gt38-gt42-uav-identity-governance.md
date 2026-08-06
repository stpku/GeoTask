# GT38–GT42: Inspection-drone identity governance after a brief tracking loss

## Scenario

A fictional inspection drone, **UAV-017**, is performing a power-line inspection inside an industrial campus:

- at 08:02, the system records the final pre-loss observation as trajectory `track_alpha`, bound to subject `provisional_alpha`;
- the drone enters a building-shadow region and is briefly lost;
- at 08:03, observation resumes five meters away, but the tracker creates a new trajectory `track_beta` and a new provisional subject `provisional_beta`;
- the two boundary observations are 60 seconds apart and both represent a `uav`.

The public story keeps the stable machine identifiers while adding human-readable labels:

| Machine identifier | Display label |
|---|---|
| `track_alpha` | pre-loss trajectory |
| `track_beta` | resumed trajectory |
| `provisional_alpha` | original UAV-017 subject |
| `provisional_beta` | post-occlusion provisional subject |

## Why the system must not merge immediately

A false merge could attach another drone's trajectory to UAV-017, corrupting mission history, risk assessment, and accountability. A missed merge would count one drone twice and split one continuous mission and risk state across two objects.

GeoTask therefore keeps identity evidence, merge proposal, proposal approval, change request, application approval, and actual application as separate responsibilities.

## Five stages

### GT38: evidence adjudication

GT37 produces only a `same_object_candidate`. GT38 additionally binds:

- a fictional asset registry reporting the same Remote ID and device serial number;
- a fictional human review confirming mission, model, operator, and temporal continuity;
- a caller-authored Assurance Profile;
- the exact bytes of the candidate, request, Provider descriptors, and responses.

The result is `same_object_confirmed`, but the only next step is `review_identity_merge`; no identity is merged.

### GT39: merge proposal

The caller selects `provisional_alpha` as the canonical subject and retains `provisional_beta` as an alias. The proposal covers only the original two trajectories and records blocking, withdrawal, approval, and reversal requirements without changing the object graph.

### GT40: proposal approval

`identity_governance_reviewer` and `world_state_maintainer` each make an explicit decision. All-role approval only makes a later bounded change request eligible:

```text
approved != identity_merge_performed
```

### GT41: change request

The request is reduced to one operation:

```text
track_beta /subject_ref
provisional_beta -> provisional_alpha
```

It also records application preconditions, post-application acceptance criteria, and an inverse rollback operation. A request is still not an application.

### GT42: application approval

`object_graph_change_owner` and `world_state_governance_reviewer` approve the GT41 request. All-role approval only makes a later bounded application Artifact eligible:

```text
application approval complete
!= application authorized
!= change applied
```

## Current boundary

At the end of GT42:

- `track_beta` still points to `provisional_beta`;
- both subject records still exist;
- the alias has not yet been written into the object graph;
- no World State has been updated;
- actual application, post-application acceptance, and successor World State require separate later Artifacts.

GT38–GT42 are five auditable steps in one operational scenario, not five unrelated application cases.
