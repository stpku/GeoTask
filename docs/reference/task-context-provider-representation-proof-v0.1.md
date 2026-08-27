# TC1-Real Provider Representation Proof v0.1

**Status:** method proof candidate

## Question

After provider completeness is proven, can the complete record count itself be treated as task-context burden without first checking whether the chosen source representation matches the task's physical-world entities?

## Recorded Phoenix evidence

The first complete IDs-first acquisition used joined Growth layer 2 (`FinalLUAUs_PopEmp`). It returned:

```text
complete features        118,190
unique newluau units          471
network bytes        172,127,458
pages                         119
```

The public service also exposes base planning-unit layer 4 (`FinalLUAUs`). The compact complete measurement for the same frozen broad region recorded:

```text
complete base units          471
unique newluau units         471
network bytes             24,237
requests                       2
```

Population semantics are related separately through table 13 (`New_Pop_Emp_Data`) using `newluau`.

## Interpretation

The joined representation repeats planning-unit geometry across related Pop/Emp records. Its complete feature cardinality is therefore not the task's minimal physical-world entity cardinality.

```text
118,190 joined features / 471 unique planning units
= about 250.9 feature records per unique planning unit
```

This is retained as **wrong-representation evidence**, not as a large R0 baseline from which GeoTask may advertise a compression rate.

The network-byte contrast must also remain non-scoring: joined layer 2 and base layer 4 do not carry identical semantics or fields. The evidence supports a representation-selection correction, not a 7,000x compression claim.

## Method rule

```text
Task requirement
  -> identify the physical-world entity/semantic unit actually required
  -> choose the least-duplicative source representation that preserves it
  -> prove provider completeness
  -> prove semantic/entity coverage
  -> only then compare scope/context burden
```

## Narrow conclusion

> Context cost can be dominated by the representation chosen before any task-scope reduction occurs.

A complete provider response can still be the wrong Task Context representation.

## Core boundary

This proof does not promote a generic `Representation` schema or source optimizer into GeoTask Core. It is benchmark/method evidence for a later cross-domain promotion review.
