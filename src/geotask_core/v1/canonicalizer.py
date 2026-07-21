"""GeoTask Core v1.0 — Document canonicalizer.

Converts legacy 0.x GeoTask documents to v1.0 Canonical IR, and also
parses v1.0 native documents directly.  Designed to be idempotent:
``canonicalize(document_to_dict(canonicalize(data)))`` produces the
same ``CanonicalDocument`` as ``canonicalize(data)``.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from geotask_core.v1.enums import LEGACY_OBJECT_TYPE_MAP, VALID_OBJECT_TYPES
from geotask_core.v1.ir import (
    Assertion,
    CanonicalDocument,
    ExecutionDefinition,
    ExecutionStep,
    GeotaskMetadata,
    GeoObject,
    OperatorContract,
    OutputContract,
    SpaceCRS,
    SpaceDefinition,
    Task,
    VerificationDefinition,
)


# -- Operator → expected input type pairs (for auto-generating assertions)

_OPERATOR_INPUT_TYPES: dict[str, list[str]] = {
    "distance_2d":                ["point", "point"],
    "line_intersects_rect":       ["polyline", "rect"],
    "point_to_line_distance_2d":  ["point", "polyline"],
    "rect_contains_point":        ["rect", "point"],
    "time_overlap":               ["time_interval", "time_interval"],
    "altitude_overlap":           ["altitude_interval", "altitude_interval"],
}

# Legacy field-name → canonical data-key for GeoObject.data
_LEGACY_OBJECT_FIELD_TO_DATA_KEY: dict[str, str] = {
    "xy":       "coordinates",
    "points":   "coordinates",
    "bbox":     "bbox",
    "interval": "interval",
    "range":    "range",
}


# -- Public API


def canonicalize(data: dict[str, Any]) -> CanonicalDocument:
    """Convert a raw GeoTask dict into a v1.0 :class:`CanonicalDocument`.

    Handles two input shapes:

    * **Legacy 0.x** — top-level ``ops`` key, ``geotask.version`` not
      starting with ``"1."``, objects with legacy field names
      (``xy``, ``points``, ``interval``, ``range``).
    * **v1.0 native** — top-level ``tasks`` key, ``geotask.schema_version``
      of ``"1.0"``, objects with ``data`` dicts.

    The function is idempotent: re-canonicalising a previously
    canonicalised document (via ``document_to_dict`` → ``canonicalize``)
    yields the same ``CanonicalDocument``.

    Args:
        data: Raw dict from YAML / JSON or a previously serialised document.

    Returns:
        A fully populated ``CanonicalDocument``.
    """
    schema = _detect_schema(data)

    if schema == "legacy":
        return _convert_legacy(data)
    # schema == "v1.0" — already canonical or natively v1.0
    return _parse_v1_native(data)


def document_to_dict(doc: CanonicalDocument) -> dict[str, Any]:
    """Serialize a :class:`CanonicalDocument` back to a plain dict.

    The output can be round-tripped through :func:`canonicalize` (idempotency).

    Args:
        doc: A CanonicalDocument instance.

    Returns:
        Plain Python dict suitable for JSON/YAML serialisation.
    """
    return _canonical_document_to_dict(doc)


# -- Schema detection


def _detect_schema(data: dict[str, Any]) -> str:
    """Return ``"legacy"`` or ``"v1.0"`` for *data*.

    Detection heuristics (checked in order):

    1. ``"ops"`` as a top-level key → legacy.
    2. ``"geotask"`` / ``"stir"`` with a ``version`` that does **not**
       start with ``"1."`` → legacy.
    3. ``"tasks"`` as a top-level key → v1.0.
    4. ``"geotask"`` with ``schema_version`` starting with ``"1."`` → v1.0.
    5. ``"_source_schema_version"`` starting with ``"1."`` → v1.0
       (already-canonicalised document).
    6. Fallback → v1.0.
    """
    # Strongest legacy signal: ops at top level
    if "ops" in data:
        return "legacy"

    # Check geotask / stir wrapper
    gt = data.get("geotask", data.get("stir"))
    if isinstance(gt, dict):
        version = str(gt.get("version", gt.get("schema_version", "")))
        if version and not version.startswith("1."):
            return "legacy"
        if version.startswith("1."):
            return "v1.0"
        if "schema_version" in gt:
            return "v1.0"

    # v1.0 signal: tasks at top level
    if "tasks" in data:
        return "v1.0"

    # Already-canonicalised signal
    if str(data.get("_source_schema_version", "")).startswith("1."):
        return "v1.0"

    # If the dict looks like a serialised CanonicalDocument (has metadata)
    if "metadata" in data and isinstance(data.get("metadata"), dict):
        return "v1.0"

    # Fallback: treat as v1.0
    return "v1.0"


# -- Legacy 0.x → v1.0 conversion


def _convert_legacy(data: dict[str, Any]) -> CanonicalDocument:
    """Convert a legacy 0.x dict to a full CanonicalDocument."""
    warnings: list[str] = []

    # -- Top-level wrappers
    gt = data.get("geotask", data.get("stir", {}))
    if not isinstance(gt, dict):
        gt = {}

    # -- Metadata
    name: str = str(gt.get("name", "unnamed"))
    doc_id = _generate_stable_id(name)
    metadata = GeotaskMetadata(
        id=doc_id,
        name=name,
        description=str(gt.get("goal", gt.get("description", ""))),
        schema_version=str(gt.get("version", "0.x")),
        language=str(gt.get("language", "en")),
        domain=str(gt.get("domain", "general_spatial")),
        created_at=str(gt.get("created_at", "")),
        tags=list(gt.get("tags", [])),
    )

    # -- Space 
    space_raw = data.get("space", {})
    if not isinstance(space_raw, dict):
        space_raw = {}
    crs_raw = space_raw.get("crs", "unknown")
    if isinstance(crs_raw, str):
        crs = SpaceCRS(
            type=_infer_crs_type(crs_raw),
            identifier=crs_raw,
        )
    elif isinstance(crs_raw, dict):
        crs = SpaceCRS(
            type=str(crs_raw.get("type", "unknown")),
            identifier=str(crs_raw.get("identifier", "")),
        )
    else:
        crs = SpaceCRS(type="unknown")

    space = SpaceDefinition(
        crs=crs,
        axes=dict(space_raw.get("axes", {})),
        horizontal_unit=str(space_raw.get("unit", space_raw.get("horizontal_unit", "meter"))),
        vertical_unit=str(space_raw.get("vertical_unit", "meter")),
        coordinate_order=list(space_raw.get("coordinate_order", ["x", "y"])),
        precision=dict(space_raw.get("precision", {})),
    )

    # -- Objects 
    objects_raw = data.get("objects", {})
    if not isinstance(objects_raw, dict):
        objects_raw = {}
    objects: dict[str, GeoObject] = {}
    for obj_id, obj_data in objects_raw.items():
        if not isinstance(obj_data, dict):
            warnings.append(f"Object '{obj_id}' is not a dict — skipping.")
            continue
        obj_type = str(obj_data.get("type", "point"))
        # Map legacy type names
        obj_type = LEGACY_OBJECT_TYPE_MAP.get(obj_type, obj_type)
        # Build data dict from legacy fields
        geo_data = _convert_legacy_object_data(obj_data, obj_type, obj_id, warnings)
        objects[str(obj_id)] = GeoObject(id=str(obj_id), type=obj_type, data=geo_data)

    # -- Operator set & contracts 
    ops_raw = data.get("ops", {})
    if not isinstance(ops_raw, dict):
        ops_raw = {}
    operator_set: list[str] = list(ops_raw.keys())
    operator_contracts: dict[str, OperatorContract] = {}
    for op_name, op_desc in ops_raw.items():
        operator_contracts[str(op_name)] = OperatorContract(
            name=str(op_name),
            version="0.x",
            description=str(op_desc) if isinstance(op_desc, str) else "",
        )

    # -- Task 
    task_raw = data.get("task", {})
    if not isinstance(task_raw, dict):
        task_raw = {}

    # -- Assertions (explicit or auto-generated) 
    explicit_assertions: list[dict[str, Any]] = list(data.get("assertions", []))
    if explicit_assertions:
        assertions = _parse_assertions(explicit_assertions, warnings)
    else:
        assertions = _auto_generate_assertions(
            operator_set=operator_set,
            objects=objects,
            warnings=warnings,
        )

    task = Task(
        id=f"{doc_id}_task_0",
        family=str(task_raw.get("family", "")),
        goal="; ".join(task_raw.get("questions", [])) if isinstance(task_raw.get("questions"), list) else str(task_raw.get("goal", "")),
        inputs=list(task_raw.get("inputs", task_raw.get("questions", []))),
        constraints=list(task_raw.get("constraints", [])),
        assertions=assertions,
        outputs=list(task_raw.get("outputs", [])),
    )
    tasks: list[Task] = [task]

    # -- Execution 
    exec_raw = data.get("execution", {})
    if not isinstance(exec_raw, dict):
        exec_raw = {}
    if exec_raw:
        execution = _parse_execution(exec_raw)
    else:
        # Auto-generate default steps from assertions
        execution_steps: list[ExecutionStep] = []
        for i, assertion in enumerate(assertions):
            if isinstance(assertion, Assertion):
                aid = assertion.id
            elif isinstance(assertion, dict):
                aid = assertion.get("id", f"step_{i}")
            else:
                aid = f"step_{i}"
            execution_steps.append(ExecutionStep(
                id=f"exec_{aid}",
                executor="local",
                assertion_refs=[aid],
            ))
        execution = ExecutionDefinition(
            mode="local_only",
            steps=execution_steps,
        )

    # -- Verification 
    verif_raw = data.get("verification", {})
    if not isinstance(verif_raw, dict):
        verif_raw = {}
    verification = VerificationDefinition(
        mode=str(verif_raw.get("mode", "none")),
        required_assurance=str(verif_raw.get("required_assurance", "unverified")),
        compare=dict(verif_raw.get("compare", {})),
        failure_policy=dict(verif_raw.get("failure_policy", {})),
    )

    # -- Output Contract 
    oc_raw = data.get("output_contract", {})
    if not isinstance(oc_raw, dict):
        oc_raw = {}
    output_contract = OutputContract(
        format=str(oc_raw.get("format", "structured")),
        required_fields=list(oc_raw.get("required_fields", [])),
        allow_additional_fields=bool(oc_raw.get("allow_additional_fields", True)),
        allow_model_inference=bool(oc_raw.get("allow_model_inference", True)),
        numeric_precision=dict(oc_raw.get("numeric_precision", {})),
        ordering=dict(oc_raw.get("ordering", {})),
    )

    # -- Expected results 
    expected_results: list[Any] = list(data.get("expected_results", []))

    # -- Extensions 
    extensions: dict[str, Any] = dict(data.get("extensions", {}))

    doc = CanonicalDocument(
        metadata=metadata,
        space=space,
        objects=objects,
        operator_set=operator_set,
        operator_contracts=operator_contracts,
        tasks=tasks,
        execution=execution,
        verification=verification,
        output_contract=output_contract,
        extensions=extensions,
        expected_results=expected_results,
        _source_schema_version="1.0",   # Mark as canonicalised for idempotency
    )

    # Attach warnings
    doc.extensions["_warnings"] = warnings

    return doc


# -- v1.0 native parsing


def _parse_v1_native(data: dict[str, Any]) -> CanonicalDocument:
    """Parse a v1.0-native (or already-canonicalised) dict into CanonicalDocument."""
    warnings: list[str] = []

    # -- Metadata 
    md = data.get("metadata", {})
    if not isinstance(md, dict) or not md:
        # Empty or non-dict metadata — try extracting from geotask wrapper
        gt = data.get("geotask", data.get("stir", {}))
        if isinstance(gt, dict):
            name = str(gt.get("name", "unnamed"))
            md = {
                "id": gt.get("id", _generate_stable_id(name)),
                "name": name,
                "description": str(gt.get("description", gt.get("goal", ""))),
                "schema_version": str(gt.get("schema_version", gt.get("version", "1.0"))),
                "language": str(gt.get("language", "en")),
                "domain": str(gt.get("domain", "general_spatial")),
                "created_at": str(gt.get("created_at", "")),
                "tags": list(gt.get("tags", [])),
            }
        elif isinstance(md, dict):
            pass  # keep empty dict
        else:
            md = {}
    metadata = GeotaskMetadata(
        id=str(md.get("id", "unnamed")),
        name=str(md.get("name", "unnamed")),
        description=str(md.get("description", "")),
        schema_version=str(md.get("schema_version", "1.0")),
        language=str(md.get("language", "en")),
        domain=str(md.get("domain", "general_spatial")),
        created_at=str(md.get("created_at", "")),
        tags=list(md.get("tags", [])),
    )

    # -- Space 
    sp = data.get("space", {})
    if not isinstance(sp, dict):
        sp = {}
    crs_raw = sp.get("crs", {})
    if isinstance(crs_raw, str):
        crs = SpaceCRS(type=_infer_crs_type(crs_raw), identifier=crs_raw)
    elif isinstance(crs_raw, dict):
        crs = SpaceCRS(
            type=str(crs_raw.get("type", "unknown")),
            identifier=str(crs_raw.get("identifier", "")),
        )
    else:
        crs = SpaceCRS(type="unknown")
    space = SpaceDefinition(
        crs=crs,
        axes=dict(sp.get("axes", {})),
        horizontal_unit=str(sp.get("horizontal_unit", sp.get("unit", "meter"))),
        vertical_unit=str(sp.get("vertical_unit", "meter")),
        coordinate_order=list(sp.get("coordinate_order", ["x", "y"])),
        precision=dict(sp.get("precision", {})),
    )

    # -- Objects 
    objects_raw = data.get("objects", {})
    if not isinstance(objects_raw, dict):
        objects_raw = {}
    objects: dict[str, GeoObject] = {}
    for obj_id, obj_data in objects_raw.items():
        if not isinstance(obj_data, dict):
            warnings.append(f"Object '{obj_id}' is not a dict — skipping.")
            continue
        obj_type = str(obj_data.get("type", "point"))
        obj_type = LEGACY_OBJECT_TYPE_MAP.get(obj_type, obj_type)
        # Check for explicit data sub-dict (canonical format)
        obj_data_dict = obj_data.get("data", {})
        if not isinstance(obj_data_dict, dict) or not obj_data_dict:
            # No explicit data dict — extract from top-level object fields
            obj_data_dict = _convert_legacy_object_data(
                obj_data, obj_type, obj_id, warnings
            )
        objects[str(obj_id)] = GeoObject(
            id=str(obj_id), type=obj_type, data=obj_data_dict
        )

    # -- Operator set 
    operator_set: list[str] = _coerce_str_list(data.get("operator_set", []))

    # -- Operator contracts 
    oc_raw = data.get("operator_contracts", {})
    operator_contracts: dict[str, OperatorContract] = {}
    if isinstance(oc_raw, dict):
        for name, cdata in oc_raw.items():
            if isinstance(cdata, dict):
                operator_contracts[str(name)] = OperatorContract(
                    name=str(name),
                    version=str(cdata.get("version", "1.0")),
                    family=str(cdata.get("family", "")),
                    description=str(cdata.get("description", "")),
                    arity=int(cdata.get("arity", 0)),
                    input_types=list(cdata.get("input_types", [])),
                    output=dict(cdata.get("output", {})),
                    deterministic=bool(cdata.get("deterministic", True)),
                    semantics=dict(cdata.get("semantics", {})),
                    model_execution=dict(cdata.get("model_execution", {})),
                    invariants=list(cdata.get("invariants", [])),
                    error_codes=list(cdata.get("error_codes", [])),
                    examples=list(cdata.get("examples", [])),
                    implementation=str(cdata.get("implementation", "")),
                )

    # -- Tasks 
    tasks_raw = data.get("tasks", [])
    tasks: list[Task] = []
    for tdata in (tasks_raw if isinstance(tasks_raw, list) else []):
        if not isinstance(tdata, dict):
            continue
        raw_assertions = tdata.get("assertions", [])
        task_assertions = _parse_assertions(
            raw_assertions if isinstance(raw_assertions, list) else [],
            warnings,
        )
        tasks.append(Task(
            id=str(tdata.get("id", "task_0")),
            family=str(tdata.get("family", "")),
            goal=str(tdata.get("goal", "")),
            inputs=list(tdata.get("inputs", [])),
            constraints=list(tdata.get("constraints", [])),
            assertions=task_assertions,
            outputs=list(tdata.get("outputs", [])),
        ))

    # -- Execution 
    exec_raw = data.get("execution", {})
    execution = _parse_execution(exec_raw if isinstance(exec_raw, dict) else {})

    # -- Verification 
    verif_raw = data.get("verification", {})
    if not isinstance(verif_raw, dict):
        verif_raw = {}
    verification = VerificationDefinition(
        mode=str(verif_raw.get("mode", "none")),
        required_assurance=str(verif_raw.get("required_assurance", "unverified")),
        compare=dict(verif_raw.get("compare", {})),
        failure_policy=dict(verif_raw.get("failure_policy", {})),
    )

    # -- Output Contract 
    oc_d = data.get("output_contract", {})
    if not isinstance(oc_d, dict):
        oc_d = {}
    output_contract = OutputContract(
        format=str(oc_d.get("format", "structured")),
        required_fields=list(oc_d.get("required_fields", [])),
        allow_additional_fields=bool(oc_d.get("allow_additional_fields", True)),
        allow_model_inference=bool(oc_d.get("allow_model_inference", True)),
        numeric_precision=dict(oc_d.get("numeric_precision", {})),
        ordering=dict(oc_d.get("ordering", {})),
    )

    # -- Remaining top-level fields 
    expected_results: list[Any] = list(data.get("expected_results", []))
    extensions: dict[str, Any] = dict(data.get("extensions", {}))

    doc = CanonicalDocument(
        metadata=metadata,
        space=space,
        objects=objects,
        operator_set=operator_set,
        operator_contracts=operator_contracts,
        tasks=tasks,
        execution=execution,
        verification=verification,
        output_contract=output_contract,
        extensions=extensions,
        expected_results=expected_results,
        _source_schema_version="1.0",
    )

    if warnings:
        doc.extensions.setdefault("_warnings", []).extend(warnings)

    return doc


# -- Legacy object data conversion


def _convert_legacy_object_data(
    obj_data: dict[str, Any],
    obj_type: str,
    obj_id: str,
    warnings: list[str],
) -> dict[str, Any]:
    """Extract GeoObject ``data`` dict from legacy field names.

    Legacy fields like ``xy``, ``points``, ``interval``, ``range`` are
    mapped to canonical keys in the ``data`` dict (``coordinates``,
    ``bbox``, etc.).
    """
    result: dict[str, Any] = {}

    for legacy_key, canonical_key in _LEGACY_OBJECT_FIELD_TO_DATA_KEY.items():
        if legacy_key in obj_data:
            result[canonical_key] = obj_data[legacy_key]

    # Carry over any other non-standard keys
    for key, value in obj_data.items():
        if key not in ("type", *list(_LEGACY_OBJECT_FIELD_TO_DATA_KEY)):
            if key not in result:
                result[key] = value

    return result


# -- Assertion helpers


def _parse_assertions(
    raw: list[dict[str, Any]],
    warnings: list[str],
) -> list[Assertion]:
    """Parse a list of assertion dicts into :class:`Assertion` objects."""
    result: list[Assertion] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            warnings.append(f"Assertion[{i}] is not a dict — skipping.")
            continue
        result.append(Assertion(
            id=str(entry.get("id", f"assertion_{i}")),
            operator=str(entry.get("operator", "")),
            object_refs=list(entry.get("object_refs", [])),
            parameters=dict(entry.get("parameters", {})),
            expected_type=str(entry.get("expected_type", "")),
            unit=str(entry.get("unit", "")),
            tolerance=float(entry.get("tolerance", 0.0)),
            depends_on=list(entry.get("depends_on", [])),
            condition=str(entry.get("condition", "")),
            on_error=str(entry.get("on_error", "stop")),
        ))
    return result


def _pick_distinct(
    candidates: list[list[GeoObject]],
    op_name: str,
    warnings: list[str],
) -> list[str]:
    """Pick distinct object refs from candidate lists, avoiding reuse.

    When the same type appears N times in the operator's input_types,
    ensures N *different* objects of that type are selected.
    """
    used: set[str] = set()
    refs: list[str] = []
    for group in candidates:
        for obj in group:
            if obj.id not in used:
                refs.append(obj.id)
                used.add(obj.id)
                break
        else:
            warnings.append(
                f"Auto-generated assertion for '{op_name}': not enough "
                f"distinct objects of required types."
            )
    return refs


def _auto_generate_assertions(
    operator_set: list[str],
    objects: dict[str, GeoObject],
    warnings: list[str],
) -> list[Assertion]:
    """Create assertions automatically from operator names.

    For each operator, attempts to find matching objects by type and
    auto-pairs them.  Emits a deprecation warning for each auto-generated
    assertion.
    """
    assertions: list[Assertion] = []

    for op_name in operator_set:
        expected_types = _OPERATOR_INPUT_TYPES.get(op_name)
        if expected_types is None:
            warnings.append(
                f"Operator '{op_name}' not recognised — cannot auto-pair objects."
            )
            continue

        # Collect objects matching each expected type
        candidates: list[list[GeoObject]] = []
        for etype in expected_types:
            matching = [o for o in objects.values() if o.type == etype]
            candidates.append(matching)

        # Auto-pair: take distinct objects, avoiding reuse when the same type
        # appears multiple times (e.g. distance_2d needs two distinct points).
        if all(candidates):
            obj_refs = _pick_distinct(candidates, op_name, warnings)
        else:
            # Fallback: try to find any objects (less specific)
            obj_refs = _fallback_pair(objects, expected_types, op_name, warnings)
            if not obj_refs:
                continue

        assertion_id = f"{op_name}_auto"
        assertions.append(Assertion(
            id=assertion_id,
            operator=op_name,
            object_refs=obj_refs,
        ))
        warnings.append(
            f"Auto-generated assertion '{assertion_id}' from operator "
            f"'{op_name}'. Consider adding explicit assertions for "
            f"deterministic execution."
        )

    return assertions


def _fallback_pair(
    objects: dict[str, GeoObject],
    expected_types: list[str],
    op_name: str,
    warnings: list[str],
) -> list[str]:
    """Fallback object pairing when exact type matches aren't found.

    Tries to pair any objects whose types appear in *expected_types*
    (order-preserving first-match).
    """
    used: set[str] = set()
    refs: list[str] = []
    for etype in expected_types:
        for obj in objects.values():
            if obj.id not in used and obj.type == etype:
                refs.append(obj.id)
                used.add(obj.id)
                break
        else:
            warnings.append(
                f"Cannot auto-pair operator '{op_name}': no object of "
                f"type '{etype}' found."
            )
    return refs if len(refs) == len(expected_types) else []


# -- Execution parsing


def _parse_execution(raw: dict[str, Any]) -> ExecutionDefinition:
    """Parse an execution definition dict."""
    steps_raw = raw.get("steps", [])
    steps: list[ExecutionStep] = []
    if isinstance(steps_raw, list):
        for s in steps_raw:
            if isinstance(s, dict):
                steps.append(ExecutionStep(
                    id=str(s.get("id", "")),
                    executor=str(s.get("executor", "local")),
                    assertion_refs=list(s.get("assertion_refs", [])),
                    operation=str(s.get("operation", "")),
                    depends_on=list(s.get("depends_on", [])),
                    on_error=str(s.get("on_error", "stop")),
                    condition=str(s.get("condition", "")),
                ))
    return ExecutionDefinition(
        mode=str(raw.get("mode", "local_only")),
        steps=steps,
        allowed_modes=list(raw.get("allowed_modes", [])),
        model_execution_limits=dict(raw.get("model_execution_limits", {})),
    )


# -- Serialisation (for idempotency)


def _canonical_document_to_dict(doc: CanonicalDocument) -> dict[str, Any]:
    """Convert a CanonicalDocument to a plain dict for round-tripping."""
    return {
        "metadata": _dataclass_to_dict(doc.metadata),
        "space": _space_to_dict(doc.space),
        "objects": {
            oid: _geo_object_to_dict(obj)
            for oid, obj in doc.objects.items()
        },
        "operator_set": list(doc.operator_set),
        "operator_contracts": {
            name: _dataclass_to_dict(contract)
            for name, contract in doc.operator_contracts.items()
        },
        "tasks": [
            _task_to_dict(t) for t in doc.tasks
        ],
        "execution": _execution_to_dict(doc.execution),
        "verification": _dataclass_to_dict(doc.verification),
        "output_contract": _dataclass_to_dict(doc.output_contract),
        "extensions": dict(doc.extensions),
        "expected_results": list(doc.expected_results),
        "_source_schema_version": doc._source_schema_version,
    }


def _space_to_dict(sp: SpaceDefinition) -> dict[str, Any]:
    return {
        "crs": _dataclass_to_dict(sp.crs),
        "axes": dict(sp.axes),
        "horizontal_unit": sp.horizontal_unit,
        "vertical_unit": sp.vertical_unit,
        "coordinate_order": list(sp.coordinate_order),
        "precision": dict(sp.precision),
    }


def _geo_object_to_dict(obj: GeoObject) -> dict[str, Any]:
    return {
        "id": obj.id,
        "type": obj.type,
        "data": dict(obj.data),
    }


def _task_to_dict(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "family": task.family,
        "goal": task.goal,
        "inputs": list(task.inputs),
        "constraints": list(task.constraints),
        "assertions": [
            _dataclass_to_dict(a) if is_dataclass(a) and not isinstance(a, type)
            else a
            for a in task.assertions
        ],
        "outputs": list(task.outputs),
    }


def _execution_to_dict(ex: ExecutionDefinition) -> dict[str, Any]:
    return {
        "mode": ex.mode,
        "steps": [
            _dataclass_to_dict(s) if is_dataclass(s) and not isinstance(s, type)
            else s
            for s in ex.steps
        ],
        "allowed_modes": list(ex.allowed_modes),
        "model_execution_limits": dict(ex.model_execution_limits),
    }


def _dataclass_to_dict(obj: Any) -> Any:
    """Convert a dataclass instance to a plain dict (recursive-safe)."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, dict):
        return {str(k): _dataclass_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_dataclass_to_dict(v) for v in obj]
    return obj


# -- Utilities


def _generate_stable_id(name: str) -> str:
    """Generate a stable document id from a human-readable name."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug if slug else "unnamed"


def _infer_crs_type(identifier: str) -> str:
    """Heuristically infer a CRS type from an identifier string."""
    identifier_lower = identifier.lower()
    if "local" in identifier_lower and ("xy" in identifier_lower or "cartesian" in identifier_lower):
        return "local_cartesian"
    if "projected" in identifier_lower or "epsg" in identifier_lower:
        return "projected"
    if "geographic" in identifier_lower or "wgs" in identifier_lower or "crs84" in identifier_lower:
        return "geographic"
    return "unknown"


def _coerce_str_list(value: Any) -> list[str]:
    """Coerce *value* to a list of strings, or return empty list."""
    if isinstance(value, list):
        return [str(v) for v in value]
    return []
