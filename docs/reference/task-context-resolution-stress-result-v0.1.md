# GeoTask Real Resolution Stress Result v0.1

**Status:** REAL STRESS GATE = PASS; CORE PROMOTION = HOLD PENDING INDEPENDENT REUSE  
**Date:** 2026-08-18  
**Source:** pinned USGS 3DEP bare-earth elevation fixture  
**Scenario:** fictional terrain-context threshold screening; no flight-safety or authorization claim

## 1. Why this result is admissible

The benchmark froze its scored inputs before reading elevation pixels:

```text
source candidate      Phoenix South Mountain
fine ROI              512 m x 512 m
fine reference        1 m / 512 x 512 / float32
resolution ladder     32 -> 16 -> 8 -> 4 -> 1 m
corridors             6 fixed 4 m-wide rectangles
thresholds            300,350,400,450,500,550,600,650 m
aggregation           exact block min/max envelope
```

Source discovery inspected only USGS product metadata. The candidate location was
not changed after fine terrain values were observed. Every one of the 6 x 8 = 48
corridor/threshold combinations is reported; no favorable subset is selected.

The acquired reference was validated as:

```text
width / height         512 / 512
CRS                    EPSG:3857
pixel size             1.0 m x 1.0 m
band / dtype           1 / float32
masked or NoData       0
fine-grid SHA-256      3e220f9bda598ede5418163b0f783be7cfc53921ef665b0ba112765cf2512f95
terrain range          449.6948 .. 655.2140 m
```

The raw TIFF and a normalized little-endian float32 grid are pinned in the
benchmark fixture for offline replay.

## 2. Frozen method

Each coarse cell stores the exact minimum and maximum of the fine reference cells
inside its support.

For a corridor and frozen threshold:

```text
any intersecting cell min >= threshold
    -> STOP_BLOCKED

all intersecting cell max < threshold
    -> STOP_CLEAR

otherwise
    -> REFINE
```

The rule is conservative. A coarse context may be ambiguous because a coarse
cell includes both corridor-relevant and off-corridor terrain, but it may not
claim a clear/block result that conflicts with the pinned fine reference.

This tests **decision-preserving coarsening**, not whether a mean-resampled raster
looks visually similar to a 1 m raster.

## 3. Real result

All 48 frozen cases replayed successfully:

```text
total cases                    48
stop at 32 m                   45
refinement cases                3
unsafe coarse stops             0
unnecessary refinements         0
```

Final resolution distribution:

```text
32 m    45 cases
16 m     2 cases
 8 m     1 case
 4 m     0 cases
 1 m     0 cases
```

Thus **93.75%** of this frozen matrix was already decision-preserving at 32 m,
while **6.25%** required finer context.

This percentage is a property of this benchmark matrix and must not be presented
as a general GeoTask rate.

## 4. The three genuine refinement cases

### A. `vertical_center @ 600 m`

```text
32 m    REFINE
16 m    STOP_BLOCKED
fine    STOP_BLOCKED
```

At 32 m no intersecting cell was definitely blocked, while two cells straddled
the threshold envelope. At 16 m one cell became definitely blocked.

### B. `vertical_west @ 600 m`

```text
32 m    REFINE
16 m    STOP_BLOCKED
fine    STOP_BLOCKED
```

The same rule resolves a different corridor without changing threshold or method.

### C. `horizontal_north @ 550 m`

```text
32 m    REFINE
16 m    REFINE
 8 m    STOP_CLEAR
fine    STOP_CLEAR
```

This case is particularly important: refinement does not merely make the system
more conservative. Finer context removes off-corridor ambiguity and proves the
corridor clear under the frozen discrete reference. The 8 m stopping margin is
approximately 1.229 m.

## 5. Safety/countermetric result

For every case:

```text
adaptive final action == 1 m reference action
```

Therefore:

```text
Unsafe Resolution Stop Rate    0 / resolution-sensitive cases
Unnecessary Refinement Rate    0 under the frozen proof rule
```

The first value is the critical countermetric. A smaller context payload would
not count as success if a coarse stop disagreed with the fine reference.

## 6. Context-burden ledger

### Task-context cell references

```text
adaptive policy       1,624 cell references
always-1m baseline   86,016 cell references
reduction             98.11198%
```

### Representation-level payload estimate

The adaptive context carries min/max float32 envelopes (8 bytes/cell). The
always-fine comparison carries one float32 elevation (4 bytes/cell):

```text
adaptive payload       12,992 bytes
always-fine payload   344,064 bytes
reduction               96.22396%
```

This is a task-context representation estimate. Metadata/serialization syntax is
not included.

## 7. Critical cost boundary: pyramid construction is not free

The current benchmark derives every resolution independently from the pinned 1 m
reference. That implementation performs:

```text
fine reference cells             262,144
five resolution levels
reference-cell reads           1,310,720
```

This derivation cost is explicitly **excluded** from the context-reduction
headline.

Therefore the real engineering claim is conditional:

> When multiresolution representations are provider-native, indexed, cached, or
> amortized across tasks, the task can carry only the coarsest representation
> that proves sufficiency and refine selectively.

The benchmark does **not** prove that downloading 1 m data and rebuilding a full
pyramid for every task is cheaper than reading 1 m context directly.

This boundary is important to GeoTask positioning: GeoTask should select and
refine task context, not become a general raster-pyramid production system.

## 8. What the experiment changes conceptually

The result does not support treating `Resolution` as an independent sequential
stage after Sufficiency.

The stronger interpretation is:

```text
current context
  -> evaluate Sufficiency for the task
  -> if task action is invariant across all admissible finer states: STOP
  -> otherwise produce a Context Gap
  -> choose a refinement action
       - finer resolution is one possible action
  -> re-evaluate Sufficiency
```

Resolution is therefore better understood as a **refinement control variable**.
Its required value is task-relative and stops as soon as the current context is
sufficient.

## 9. What this experiment proves

Within one real physical-world terrain scenario, it proves that:

1. one frozen sufficiency rule can correctly handle both `STOP` and `REFINE`;
2. finer data is often unnecessary even when available;
3. the need to refine is tied to task-action ambiguity, not to a universal meter
   threshold;
4. refinement can resolve toward either `CLEAR` or `BLOCKED`;
5. the same rule can preserve fine-reference action while materially reducing
   carried context under a reusable multiresolution representation.

## 10. What it does not prove

It does not prove that:

- 32 m is generally sufficient for low-altitude tasks;
- the chosen terrain threshold is a real aviation clearance rule;
- 96.22% is a general GeoTask cost reduction;
- DEM alone is sufficient flight context;
- every domain can expose conservative min/max envelopes;
- GeoTask should immediately add an automatic Resolution engine to Core.

## 11. Promotion verdict

The **first real Resolution Stress Gate passes**:

```text
real STOP control                         PASS
real REFINE control                       PASS
same rule handles both                    PASS
unsafe stop                               0
unnecessary refinement                    0
frozen inputs before fine observation     PASS
cost boundary explicit                    PASS
```

However GeoTask's cross-line Promotion discipline requires reuse beyond a single
terrain experiment before a general method enters Core.

Therefore:

> **Decision-Preserving Resolution / Sufficiency-Guided Refinement is now a
> validated method candidate.**

> **Automatic Resolution Core promotion remains HOLD until a second independent
> physical-world task reproduces the same abstraction without terrain-specific
> semantics.**
