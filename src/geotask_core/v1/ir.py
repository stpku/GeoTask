"""v1.0 Canonical Intermediate Representation dataclasses.

The Canonical IR is the single source of truth for all v1 modules:
  - canonicalizer.py  — converts raw YAML/DSL into CanonicalDocument
  - validator.py      — validates CanonicalDocument structure and constraints
  - executor.py       — executes tasks from CanonicalDocument
  - result_builder.py — builds structured results from execution output

All v1 modules read and write these dataclass structures.
No validation or conversion logic lives here — this is pure data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # geotask_core.v1.enums imports go here to avoid circular imports


# ── Version & Metadata ──────────────────────────────────────────────────────


@dataclass
class GeotaskVersion:
    """GeoTask IR version info."""
    version: str              # Package version like "0.1.0"
    schema_version: str       # Schema version like "1.0"


@dataclass
class GeotaskMetadata:
    """geotask section metadata."""
    id: str
    name: str
    description: str = ""
    schema_version: str = "1.0"
    language: str = "en"
    domain: str = "general_spatial"
    created_at: str = ""
    tags: list = field(default_factory=list)


# ── Space Definition ────────────────────────────────────────────────────────


@dataclass
class SpaceCRS:
    """Coordinate Reference System descriptor."""
    type: str                 # local_cartesian, projected, geographic, unknown
    identifier: str = ""


@dataclass
class SpaceDefinition:
    """Spatial reference frame definition."""
    crs: SpaceCRS
    axes: dict = field(default_factory=dict)
    horizontal_unit: str = "meter"
    vertical_unit: str = "meter"
    coordinate_order: list = field(default_factory=lambda: ["x", "y"])
    precision: dict = field(default_factory=dict)


# ── Geo Objects ─────────────────────────────────────────────────────────────


@dataclass
class GeoObject:
    """A spatial or temporal object within a GeoTask document.

    Supported types and their data formats:
      - point:             data = {"coordinates": [x, y]} or {"xy": [x, y]} (compat)
      - polyline:          data = {"coordinates": [[x1,y1], ...]} or {"points": [...]}
      - rect:              data = {"bbox": [min_x, min_y, max_x, max_y]}
      - time_interval:     data = {"start": "08:00", "end": "10:00"} or {"interval": [...]}
      - altitude_interval: data = {"min": 100, "max": 200, "unit": "meter", "datum": "relative"}
                           or {"range": [...]}
      - feature_collection: data = {"feature_type": "point", "features": [...]}
    """
    id: str
    type: str                # point, polyline, rect, time_interval, altitude_interval, feature_collection
    data: dict = field(default_factory=dict)


# ── Operator Contracts ──────────────────────────────────────────────────────


@dataclass
class OperatorContract:
    """Full contract for a single spatial operator."""
    name: str
    version: str = "1.0"
    family: str = ""
    description: str = ""
    arity: int = 0
    input_types: list = field(default_factory=list)
    output: dict = field(default_factory=dict)
    deterministic: bool = True
    semantics: dict = field(default_factory=dict)
    model_execution: dict = field(default_factory=dict)
    invariants: list = field(default_factory=list)
    error_codes: list = field(default_factory=list)
    examples: list = field(default_factory=list)
    implementation: str = ""


# ── Assertions ──────────────────────────────────────────────────────────────


@dataclass
class Assertion:
    """A verifiable proposition about spatial objects or their relationships."""
    id: str
    operator: str
    object_refs: list = field(default_factory=list)
    parameters: dict = field(default_factory=dict)
    expected_type: str = ""
    unit: str = ""
    tolerance: float = 0.0
    depends_on: list = field(default_factory=list)
    condition: str = ""
    on_error: str = "stop"


# ── Tasks ───────────────────────────────────────────────────────────────────


@dataclass
class Task:
    """A spatial task composed of inputs, constraints, assertions, and outputs."""
    id: str
    family: str = ""
    goal: str = ""
    inputs: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    assertions: list = field(default_factory=list)       # list[Assertion]
    outputs: list = field(default_factory=list)


# ── Execution ───────────────────────────────────────────────────────────────


@dataclass
class ExecutionStep:
    """A single step within an execution plan."""
    id: str
    executor: str            # model, local, connector, human, runtime
    assertion_refs: list = field(default_factory=list)
    operation: str = ""
    depends_on: list = field(default_factory=list)
    on_error: str = "stop"
    condition: str = ""


@dataclass
class ExecutionDefinition:
    """How tasks should be executed."""
    mode: str = "local_only"  # model_only, local_only, hybrid, shadow_compare
    steps: list = field(default_factory=list)            # list[ExecutionStep]
    allowed_modes: list = field(default_factory=list)
    model_execution_limits: dict = field(default_factory=dict)


# ── Verification ────────────────────────────────────────────────────────────


@dataclass
class VerificationDefinition:
    """Post-execution verification policy."""
    mode: str = "none"
    required_assurance: str = "unverified"
    compare: dict = field(default_factory=dict)
    failure_policy: dict = field(default_factory=dict)


# ── Output Contracts ───────────────────────────────────────────────────────


@dataclass
class OutputContract:
    """Constraints on the shape of result output."""
    format: str = "structured"
    required_fields: list = field(default_factory=list)
    allow_additional_fields: bool = True
    allow_model_inference: bool = True
    numeric_precision: dict = field(default_factory=dict)
    ordering: dict = field(default_factory=dict)


# ── Canonical Document ──────────────────────────────────────────────────────


@dataclass
class CanonicalDocument:
    """The complete v1.0 Canonical IR document.

    This is the root object that flows through the entire v1 pipeline:
    Raw YAML/DSL → CanonicalDocument → validated → executed → results.
    """
    metadata: GeotaskMetadata
    space: SpaceDefinition
    objects: dict = field(default_factory=dict)          # id -> GeoObject
    operator_set: list = field(default_factory=list)      # list of operator names
    operator_contracts: dict = field(default_factory=dict) # name -> OperatorContract
    tasks: list = field(default_factory=list)             # list[Task]
    execution: ExecutionDefinition = field(default_factory=lambda: ExecutionDefinition())
    verification: VerificationDefinition = field(default_factory=lambda: VerificationDefinition())
    output_contract: OutputContract = field(default_factory=lambda: OutputContract())
    extensions: dict = field(default_factory=dict)
    expected_results: list = field(default_factory=list)
    _source_schema_version: str = "0.x"                   # Track original format
