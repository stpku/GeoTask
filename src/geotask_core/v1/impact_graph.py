"""Public Impact Graph v0.1 contract.

An Impact Graph binds one immutable World State and exact source Artifacts to a
finite directed acyclic graph of declared downstream impact. It records roots,
affected paths, assertions, outputs, actions, correction changes, and explicit
reevaluation targets. Loading validates graph structure, reference closure,
aggregate state, reachability, and deterministic fingerprinting. Binding
validation resolves Discrepancy Report and Correction Request entities and
checks edge semantics against their declared impact and correction contracts.

Validation does not discover impact, execute propagation, apply a correction,
materialize a World State, rerun a task, evaluate a target, release an output,
or authorize an action.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import AbstractSet, Mapping, Sequence

from geotask_core.v1.correction_request import CorrectionRequest
from geotask_core.v1.discrepancy_report import DiscrepancyFinding, DiscrepancyReport
from geotask_core.v1.world_state import WorldState


IMPACT_GRAPH_ARTIFACT_ID = "geotask.impact-graph"
IMPACT_GRAPH_SCHEMA_ID = (
    "https://stpku.github.io/GeoTask/schemas/geotask-impact-graph-v0.1.schema.json"
)
IMPACT_GRAPH_SCHEMA_VERSION = "0.1"
IMPACT_GRAPH_FORMAT_VERSION = "0.1"

IMPACT_GRAPH_STATES = frozenset({"mapped", "partial", "blocked", "unknown"})
IMPACT_ENTITY_KINDS = frozenset(
    {"discrepancy", "correction_change", "acceptance_criterion", "review_requirement"}
)
IMPACT_NODE_KINDS = frozenset(
    {
        "world_state_path",
        "discrepancy",
        "correction_change",
        "acceptance_criterion",
        "review_requirement",
        "assertion",
        "output",
        "action",
        "artifact",
    }
)
IMPACT_NODE_STATES = frozenset(
    {"root", "affected", "blocked", "requires_recheck", "unknown"}
)
IMPACT_EDGE_KINDS = frozenset(
    {"changes", "invalidates", "affects", "blocks", "requires", "requires_recheck", "guards"}
)
IMPACT_EDGE_STATES = frozenset({"confirmed", "potential", "unknown"})
REEVALUATION_TARGET_STATES = frozenset({"required", "blocked", "not_required", "unknown"})


class ImpactGraphFormatError(ValueError):
    """Raised when an Impact Graph payload violates the v0.1 contract."""


def _fail(path: str, message: str) -> None:
    raise ImpactGraphFormatError(f"{path}: {message}")


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _exact_fields(
    value: Mapping[str, object],
    path: str,
    *,
    required: AbstractSet[str],
    optional: AbstractSet[str] = frozenset(),
) -> None:
    missing = sorted(required - set(value))
    if missing:
        _fail(path, "missing required fields: " + ", ".join(missing))
    unknown = sorted(set(value) - required - optional)
    if unknown:
        _fail(path, "contains unknown fields: " + ", ".join(unknown))


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")
    return value


def _enum(value: object, path: str, allowed: frozenset[str]) -> str:
    text = _string(value, path)
    if text not in allowed:
        _fail(path, "must be one of: " + ", ".join(sorted(allowed)))
    return text


def _positive_integer(value: object, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        _fail(path, "must be an integer greater than or equal to 1")
    return value


def _timestamp(value: object, path: str) -> tuple[str, datetime]:
    text = _string(value, path)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ImpactGraphFormatError(f"{path}: must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must include a timezone offset")
    return text, parsed


def _sha256(value: object, path: str) -> str:
    text = _string(value, path)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        _fail(path, "must be a lowercase 64-character SHA-256 hexadecimal digest")
    return text


def _string_list(
    value: object,
    path: str,
    *,
    non_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array of non-empty strings")
    if non_empty and not value:
        _fail(path, "must contain at least one item")
    items: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _string(item, f"{path}[{index}]")
        if text in seen:
            _fail(f"{path}[{index}]", f"duplicates {text!r}")
        seen.add(text)
        items.append(text)
    return tuple(items)


def _json_pointer(value: object, path: str) -> str:
    pointer = _string(value, path)
    if not pointer.startswith("/") or pointer.endswith("/"):
        _fail(path, "must be a non-root JSON Pointer without a trailing slash")
    segments = pointer.split("/")[1:]
    if not segments or any(not segment for segment in segments):
        _fail(path, "must not contain an empty path segment")
    for segment in segments:
        index = 0
        while index < len(segment):
            if segment[index] == "~":
                if index + 1 >= len(segment) or segment[index + 1] not in {"0", "1"}:
                    _fail(path, "contains an invalid JSON Pointer escape")
                index += 2
            else:
                index += 1
    return pointer


def _closed_refs(
    refs: tuple[str, ...],
    path: str,
    declared: AbstractSet[str],
    declaration_path: str,
) -> None:
    for index, ref in enumerate(refs):
        if ref not in declared:
            _fail(f"{path}[{index}]", f"must be declared in {declaration_path}: {ref!r}")


@dataclass(frozen=True)
class ImpactArtifactRef:
    ref_id: str
    artifact_id: str
    schema_version: str
    instance_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ref_id": self.ref_id,
            "artifact_id": self.artifact_id,
            "schema_version": self.schema_version,
            "instance_id": self.instance_id,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ImpactWorldStateRef:
    ref_id: str
    artifact_id: str
    schema_version: str
    world_state_id: str
    revision: int
    as_of: str
    semantic_fingerprint: str
    content_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ref_id": self.ref_id,
            "artifact_id": self.artifact_id,
            "schema_version": self.schema_version,
            "world_state_id": self.world_state_id,
            "revision": self.revision,
            "as_of": self.as_of,
            "semantic_fingerprint": self.semantic_fingerprint,
            "content_sha256": self.content_sha256,
        }


@dataclass(frozen=True)
class ImpactEntityRef:
    id: str
    kind: str
    artifact_ref: str
    entity_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "artifact_ref": self.artifact_ref,
            "entity_id": self.entity_id,
        }


@dataclass(frozen=True)
class ImpactNode:
    id: str
    kind: str
    identity: str
    impact_state: str
    reason: str
    basis_refs: tuple[str, ...]
    entity_ref: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "kind": self.kind,
            "identity": self.identity,
            "impact_state": self.impact_state,
            "reason": self.reason,
            "basis_refs": sorted(self.basis_refs),
        }
        if self.entity_ref is not None:
            payload["entity_ref"] = self.entity_ref
        return payload


@dataclass(frozen=True)
class ImpactEdge:
    id: str
    kind: str
    from_node: str
    to_node: str
    state: str
    reason: str
    basis_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "state": self.state,
            "reason": self.reason,
            "basis_refs": sorted(self.basis_refs),
        }


@dataclass(frozen=True)
class ReevaluationTarget:
    id: str
    node_ref: str
    state: str
    reason: str
    input_node_refs: tuple[str, ...]
    prerequisite_node_refs: tuple[str, ...]
    basis_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "node_ref": self.node_ref,
            "state": self.state,
            "reason": self.reason,
            "input_node_refs": sorted(self.input_node_refs),
            "prerequisite_node_refs": sorted(self.prerequisite_node_refs),
            "basis_refs": sorted(self.basis_refs),
        }


@dataclass(frozen=True)
class ImpactGraph:
    graph_id: str
    recorded_at: str
    state: str
    reason: str
    world_state: ImpactWorldStateRef
    artifact_refs: tuple[ImpactArtifactRef, ...]
    entity_refs: tuple[ImpactEntityRef, ...]
    root_node_refs: tuple[str, ...]
    nodes: tuple[ImpactNode, ...]
    edges: tuple[ImpactEdge, ...]
    reevaluation_targets: tuple[ReevaluationTarget, ...]
    blocked_outputs: tuple[str, ...]
    blocked_actions: tuple[str, ...]

    def all_artifact_refs(self) -> tuple[ImpactWorldStateRef | ImpactArtifactRef, ...]:
        return (self.world_state, *self.artifact_refs)

    def to_dict(self) -> dict[str, object]:
        return {
            "impact_graph": {
                "schema_id": IMPACT_GRAPH_SCHEMA_ID,
                "schema_version": IMPACT_GRAPH_SCHEMA_VERSION,
                "graph_id": self.graph_id,
                "recorded_at": self.recorded_at,
                "state": self.state,
                "reason": self.reason,
                "world_state": self.world_state.to_dict(),
                "artifact_refs": [
                    item.to_dict()
                    for item in sorted(self.artifact_refs, key=lambda item: item.ref_id)
                ],
                "entity_refs": [
                    item.to_dict()
                    for item in sorted(self.entity_refs, key=lambda item: item.id)
                ],
                "root_node_refs": sorted(self.root_node_refs),
                "nodes": [
                    item.to_dict() for item in sorted(self.nodes, key=lambda item: item.id)
                ],
                "edges": [
                    item.to_dict() for item in sorted(self.edges, key=lambda item: item.id)
                ],
                "reevaluation_targets": [
                    item.to_dict()
                    for item in sorted(self.reevaluation_targets, key=lambda item: item.id)
                ],
                "blocked_outputs": sorted(self.blocked_outputs),
                "blocked_actions": sorted(self.blocked_actions),
            }
        }

    def semantic_fingerprint(self) -> str:
        raw = json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _load_world_state_ref(value: object) -> tuple[ImpactWorldStateRef, datetime]:
    path = "impact_graph.world_state"
    ref = _mapping(value, path)
    _exact_fields(
        ref,
        path,
        required={
            "ref_id",
            "artifact_id",
            "schema_version",
            "world_state_id",
            "revision",
            "as_of",
            "semantic_fingerprint",
            "content_sha256",
        },
    )
    if ref["artifact_id"] != "geotask.world-state":
        _fail(f"{path}.artifact_id", "must equal 'geotask.world-state'")
    if ref["schema_version"] != "0.1":
        _fail(f"{path}.schema_version", "must equal '0.1'")
    as_of_text, as_of = _timestamp(ref["as_of"], f"{path}.as_of")
    return (
        ImpactWorldStateRef(
            ref_id=_string(ref["ref_id"], f"{path}.ref_id"),
            artifact_id="geotask.world-state",
            schema_version="0.1",
            world_state_id=_string(ref["world_state_id"], f"{path}.world_state_id"),
            revision=_positive_integer(ref["revision"], f"{path}.revision"),
            as_of=as_of_text,
            semantic_fingerprint=_sha256(
                ref["semantic_fingerprint"], f"{path}.semantic_fingerprint"
            ),
            content_sha256=_sha256(ref["content_sha256"], f"{path}.content_sha256"),
        ),
        as_of,
    )


def _load_artifact_refs(value: object) -> tuple[ImpactArtifactRef, ...]:
    path = "impact_graph.artifact_refs"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if not value:
        _fail(path, "must contain at least one item")
    items: list[ImpactArtifactRef] = []
    ref_ids: set[str] = set()
    instance_ids: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={"ref_id", "artifact_id", "schema_version", "instance_id", "content_sha256"},
        )
        ref_id = _string(item["ref_id"], f"{item_path}.ref_id")
        instance_id = _string(item["instance_id"], f"{item_path}.instance_id")
        if ref_id in ref_ids:
            _fail(f"{item_path}.ref_id", f"duplicates {ref_id!r}")
        if instance_id in instance_ids:
            _fail(f"{item_path}.instance_id", f"duplicates {instance_id!r}")
        ref_ids.add(ref_id)
        instance_ids.add(instance_id)
        items.append(
            ImpactArtifactRef(
                ref_id=ref_id,
                artifact_id=_string(item["artifact_id"], f"{item_path}.artifact_id"),
                schema_version=_string(
                    item["schema_version"], f"{item_path}.schema_version"
                ),
                instance_id=instance_id,
                content_sha256=_sha256(
                    item["content_sha256"], f"{item_path}.content_sha256"
                ),
            )
        )
    if not any(item.artifact_id == "geotask.discrepancy-report" for item in items):
        _fail(path, "must include at least one geotask.discrepancy-report reference")
    for item in items:
        if item.artifact_id == "geotask.discrepancy-report" and item.schema_version != "0.1":
            _fail(path, "geotask.discrepancy-report references must use schema_version '0.1'")
        if item.artifact_id == "geotask.correction-request" and item.schema_version != "0.1":
            _fail(path, "geotask.correction-request references must use schema_version '0.1'")
    return tuple(sorted(items, key=lambda item: item.ref_id))


def _load_entity_refs(
    value: object,
    artifacts_by_ref: Mapping[str, ImpactArtifactRef],
) -> tuple[ImpactEntityRef, ...]:
    path = "impact_graph.entity_refs"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if not value:
        _fail(path, "must contain at least one item")
    items: list[ImpactEntityRef] = []
    ids: set[str] = set()
    pairs: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(item, item_path, required={"id", "kind", "artifact_ref", "entity_id"})
        identifier = _string(item["id"], f"{item_path}.id")
        kind = _enum(item["kind"], f"{item_path}.kind", IMPACT_ENTITY_KINDS)
        artifact_ref = _string(item["artifact_ref"], f"{item_path}.artifact_ref")
        entity_id = _string(item["entity_id"], f"{item_path}.entity_id")
        if identifier in ids:
            _fail(f"{item_path}.id", f"duplicates {identifier!r}")
        if artifact_ref not in artifacts_by_ref:
            _fail(
                f"{item_path}.artifact_ref",
                "must be declared in impact_graph.artifact_refs",
            )
        artifact_id = artifacts_by_ref[artifact_ref].artifact_id
        if kind == "discrepancy" and artifact_id != "geotask.discrepancy-report":
            _fail(f"{item_path}.artifact_ref", "discrepancy entities require a Discrepancy Report")
        if kind != "discrepancy" and artifact_id != "geotask.correction-request":
            _fail(
                f"{item_path}.artifact_ref",
                f"{kind} entities require a Correction Request",
            )
        pair = (kind, artifact_ref, entity_id)
        if pair in pairs:
            _fail(item_path, f"duplicates entity binding {pair!r}")
        ids.add(identifier)
        pairs.add(pair)
        items.append(
            ImpactEntityRef(
                id=identifier,
                kind=kind,
                artifact_ref=artifact_ref,
                entity_id=entity_id,
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def _load_nodes(
    value: object,
    *,
    entity_by_id: Mapping[str, ImpactEntityRef],
    artifact_refs: AbstractSet[str],
) -> tuple[ImpactNode, ...]:
    path = "impact_graph.nodes"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if not value:
        _fail(path, "must contain at least one item")
    items: list[ImpactNode] = []
    ids: set[str] = set()
    identities: set[tuple[str, str]] = set()
    entity_kinds = {
        "discrepancy": "discrepancy",
        "correction_change": "correction_change",
        "acceptance_criterion": "acceptance_criterion",
        "review_requirement": "review_requirement",
    }
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={"id", "kind", "identity", "impact_state", "reason", "basis_refs"},
            optional={"entity_ref"},
        )
        identifier = _string(item["id"], f"{item_path}.id")
        kind = _enum(item["kind"], f"{item_path}.kind", IMPACT_NODE_KINDS)
        identity = _string(item["identity"], f"{item_path}.identity")
        if kind == "world_state_path":
            identity = _json_pointer(identity, f"{item_path}.identity")
        if identifier in ids:
            _fail(f"{item_path}.id", f"duplicates {identifier!r}")
        identity_key = (kind, identity)
        if identity_key in identities:
            _fail(item_path, f"duplicates node identity {identity_key!r}")
        ids.add(identifier)
        identities.add(identity_key)
        basis_refs = _string_list(
            item["basis_refs"], f"{item_path}.basis_refs", non_empty=True
        )
        _closed_refs(
            basis_refs,
            f"{item_path}.basis_refs",
            artifact_refs,
            "impact_graph artifact references",
        )
        entity_ref = (
            _string(item["entity_ref"], f"{item_path}.entity_ref")
            if "entity_ref" in item
            else None
        )
        if kind in entity_kinds:
            if entity_ref is None or entity_ref not in entity_by_id:
                _fail(f"{item_path}.entity_ref", f"kind {kind!r} requires a declared entity_ref")
            if entity_by_id[entity_ref].kind != entity_kinds[kind]:
                _fail(f"{item_path}.entity_ref", f"must reference entity kind {entity_kinds[kind]!r}")
            if identity != entity_ref:
                _fail(f"{item_path}.identity", "entity-backed node identity must equal entity_ref")
            if entity_by_id[entity_ref].artifact_ref not in basis_refs:
                _fail(
                    f"{item_path}.basis_refs",
                    "entity-backed nodes must include the bound source Artifact ref",
                )
        elif entity_ref is not None:
            _fail(f"{item_path}.entity_ref", f"kind {kind!r} forbids entity_ref")
        if kind == "artifact" and identity not in artifact_refs:
            _fail(f"{item_path}.identity", "artifact nodes must identify a declared artifact ref")
        impact_state = _enum(
            item["impact_state"], f"{item_path}.impact_state", IMPACT_NODE_STATES
        )
        if impact_state == "root" and kind not in {
            "discrepancy",
            "correction_change",
            "world_state_path",
            "artifact",
        }:
            _fail(
                f"{item_path}.impact_state",
                "root state is limited to discrepancy, correction_change, world_state_path, or artifact nodes",
            )
        if impact_state == "blocked" and kind not in {"output", "action"}:
            _fail(
                f"{item_path}.impact_state",
                "blocked state is limited to output or action nodes",
            )
        if impact_state == "requires_recheck" and kind not in {"assertion", "output"}:
            _fail(
                f"{item_path}.impact_state",
                "requires_recheck state is limited to assertion or output nodes",
            )
        items.append(
            ImpactNode(
                id=identifier,
                kind=kind,
                identity=identity,
                impact_state=impact_state,
                reason=_string(item["reason"], f"{item_path}.reason"),
                basis_refs=tuple(sorted(basis_refs)),
                entity_ref=entity_ref,
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def _load_edges(
    value: object,
    *,
    node_refs: AbstractSet[str],
    artifact_refs: AbstractSet[str],
) -> tuple[ImpactEdge, ...]:
    path = "impact_graph.edges"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if not value:
        _fail(path, "must contain at least one item")
    items: list[ImpactEdge] = []
    ids: set[str] = set()
    triples: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={"id", "kind", "from_node", "to_node", "state", "reason", "basis_refs"},
        )
        identifier = _string(item["id"], f"{item_path}.id")
        kind = _enum(item["kind"], f"{item_path}.kind", IMPACT_EDGE_KINDS)
        from_node = _string(item["from_node"], f"{item_path}.from_node")
        to_node = _string(item["to_node"], f"{item_path}.to_node")
        if identifier in ids:
            _fail(f"{item_path}.id", f"duplicates {identifier!r}")
        if from_node not in node_refs or to_node not in node_refs:
            _fail(item_path, "from_node and to_node must be declared in impact_graph.nodes")
        if from_node == to_node:
            _fail(item_path, "self-loop edges are forbidden")
        triple = (kind, from_node, to_node)
        if triple in triples:
            _fail(item_path, f"duplicates edge {triple!r}")
        ids.add(identifier)
        triples.add(triple)
        basis_refs = _string_list(
            item["basis_refs"], f"{item_path}.basis_refs", non_empty=True
        )
        _closed_refs(
            basis_refs,
            f"{item_path}.basis_refs",
            artifact_refs,
            "impact_graph artifact references",
        )
        items.append(
            ImpactEdge(
                id=identifier,
                kind=kind,
                from_node=from_node,
                to_node=to_node,
                state=_enum(item["state"], f"{item_path}.state", IMPACT_EDGE_STATES),
                reason=_string(item["reason"], f"{item_path}.reason"),
                basis_refs=tuple(sorted(basis_refs)),
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def _adjacency(nodes: Sequence[ImpactNode], edges: Sequence[ImpactEdge]) -> dict[str, set[str]]:
    result = {node.id: set() for node in nodes}
    for edge in edges:
        result[edge.from_node].add(edge.to_node)
    return result


def _reachable(start_refs: Sequence[str], adjacency: Mapping[str, AbstractSet[str]]) -> set[str]:
    seen: set[str] = set(start_refs)
    stack = list(start_refs)
    while stack:
        current = stack.pop()
        for target in adjacency[current]:
            if target not in seen:
                seen.add(target)
                stack.append(target)
    return seen


def _is_reachable(source: str, target: str, adjacency: Mapping[str, AbstractSet[str]]) -> bool:
    return target in _reachable((source,), adjacency)


def _validate_dag(nodes: Sequence[ImpactNode], edges: Sequence[ImpactEdge]) -> None:
    adjacency = _adjacency(nodes, edges)
    state: dict[str, int] = {node.id: 0 for node in nodes}

    def visit(node_ref: str) -> None:
        state[node_ref] = 1
        for target in adjacency[node_ref]:
            if state[target] == 1:
                _fail("impact_graph.edges", f"cycle detected through node {target!r}")
            if state[target] == 0:
                visit(target)
        state[node_ref] = 2

    for node in nodes:
        if state[node.id] == 0:
            visit(node.id)


def _load_targets(
    value: object,
    *,
    nodes_by_id: Mapping[str, ImpactNode],
    artifact_refs: AbstractSet[str],
    adjacency: Mapping[str, AbstractSet[str]],
) -> tuple[ReevaluationTarget, ...]:
    path = "impact_graph.reevaluation_targets"
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(path, "must be an array")
    if not value:
        _fail(path, "must contain at least one item")
    items: list[ReevaluationTarget] = []
    ids: set[str] = set()
    target_nodes: set[str] = set()
    allowed_target_kinds = {"world_state_path", "assertion", "output", "action", "artifact"}
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _mapping(raw, item_path)
        _exact_fields(
            item,
            item_path,
            required={
                "id",
                "node_ref",
                "state",
                "reason",
                "input_node_refs",
                "prerequisite_node_refs",
                "basis_refs",
            },
        )
        identifier = _string(item["id"], f"{item_path}.id")
        node_ref = _string(item["node_ref"], f"{item_path}.node_ref")
        if identifier in ids:
            _fail(f"{item_path}.id", f"duplicates {identifier!r}")
        if node_ref in target_nodes:
            _fail(f"{item_path}.node_ref", f"duplicates target node {node_ref!r}")
        if node_ref not in nodes_by_id:
            _fail(f"{item_path}.node_ref", "must be declared in impact_graph.nodes")
        if nodes_by_id[node_ref].kind not in allowed_target_kinds:
            _fail(f"{item_path}.node_ref", "targets must reference a reevaluable node kind")
        ids.add(identifier)
        target_nodes.add(node_ref)
        inputs = _string_list(
            item["input_node_refs"], f"{item_path}.input_node_refs", non_empty=True
        )
        prerequisites = _string_list(
            item["prerequisite_node_refs"], f"{item_path}.prerequisite_node_refs"
        )
        for label, refs in (("input_node_refs", inputs), ("prerequisite_node_refs", prerequisites)):
            _closed_refs(refs, f"{item_path}.{label}", set(nodes_by_id), "impact_graph.nodes")
            for ref in refs:
                if ref == node_ref or not _is_reachable(ref, node_ref, adjacency):
                    _fail(
                        f"{item_path}.{label}",
                        f"node {ref!r} must be a strict graph ancestor of target {node_ref!r}",
                    )
        basis_refs = _string_list(
            item["basis_refs"], f"{item_path}.basis_refs", non_empty=True
        )
        _closed_refs(
            basis_refs,
            f"{item_path}.basis_refs",
            artifact_refs,
            "impact_graph artifact references",
        )
        state = _enum(
            item["state"], f"{item_path}.state", REEVALUATION_TARGET_STATES
        )
        target_node = nodes_by_id[node_ref]
        if set(inputs) & set(prerequisites):
            _fail(
                item_path,
                "input_node_refs and prerequisite_node_refs must be disjoint",
            )
        if state == "blocked":
            if not prerequisites:
                _fail(
                    f"{item_path}.prerequisite_node_refs",
                    "blocked targets require prerequisites",
                )
            if target_node.impact_state != "blocked":
                _fail(
                    f"{item_path}.node_ref",
                    "blocked targets must reference a blocked node",
                )
        elif state == "required" and target_node.impact_state not in {
            "affected",
            "requires_recheck",
        }:
            _fail(
                f"{item_path}.node_ref",
                "required targets must reference an affected or requires_recheck node",
            )
        elif state == "unknown" and target_node.impact_state != "unknown":
            _fail(
                f"{item_path}.node_ref",
                "unknown targets must reference an unknown node",
            )
        elif state == "not_required" and target_node.impact_state in {
            "blocked",
            "requires_recheck",
            "unknown",
        }:
            _fail(
                f"{item_path}.node_ref",
                "not_required targets cannot reference blocked, requires_recheck, or unknown nodes",
            )
        items.append(
            ReevaluationTarget(
                id=identifier,
                node_ref=node_ref,
                state=state,
                reason=_string(item["reason"], f"{item_path}.reason"),
                input_node_refs=tuple(sorted(inputs)),
                prerequisite_node_refs=tuple(sorted(prerequisites)),
                basis_refs=tuple(sorted(basis_refs)),
            )
        )
    return tuple(sorted(items, key=lambda item: item.id))


def load_impact_graph(payload: Mapping[str, object]) -> ImpactGraph:
    """Load and strictly validate one Impact Graph v0.1 payload."""

    root = _mapping(payload, "root")
    _exact_fields(root, "root", required={"impact_graph"})
    body = _mapping(root["impact_graph"], "impact_graph")
    _exact_fields(
        body,
        "impact_graph",
        required={
            "schema_id",
            "schema_version",
            "graph_id",
            "recorded_at",
            "state",
            "reason",
            "world_state",
            "artifact_refs",
            "entity_refs",
            "root_node_refs",
            "nodes",
            "edges",
            "reevaluation_targets",
            "blocked_outputs",
            "blocked_actions",
        },
    )
    if body["schema_id"] != IMPACT_GRAPH_SCHEMA_ID:
        _fail("impact_graph.schema_id", f"must equal {IMPACT_GRAPH_SCHEMA_ID!r}")
    if body["schema_version"] != IMPACT_GRAPH_SCHEMA_VERSION:
        _fail("impact_graph.schema_version", f"must equal {IMPACT_GRAPH_SCHEMA_VERSION!r}")

    recorded_at_text, recorded_at = _timestamp(body["recorded_at"], "impact_graph.recorded_at")
    world_state, as_of = _load_world_state_ref(body["world_state"])
    if recorded_at < as_of:
        _fail("impact_graph.recorded_at", "must not be earlier than world_state.as_of")

    artifact_refs = _load_artifact_refs(body["artifact_refs"])
    if world_state.ref_id in {item.ref_id for item in artifact_refs}:
        _fail("impact_graph.world_state.ref_id", "must be unique across all artifact references")
    artifacts_by_ref = {item.ref_id: item for item in artifact_refs}
    entity_refs = _load_entity_refs(body["entity_refs"], artifacts_by_ref)
    entity_by_id = {item.id: item for item in entity_refs}
    declared_artifact_refs = frozenset({world_state.ref_id, *artifacts_by_ref})
    nodes = _load_nodes(
        body["nodes"],
        entity_by_id=entity_by_id,
        artifact_refs=declared_artifact_refs,
    )
    nodes_by_id = {item.id: item for item in nodes}
    root_node_refs = _string_list(
        body["root_node_refs"], "impact_graph.root_node_refs", non_empty=True
    )
    _closed_refs(
        root_node_refs,
        "impact_graph.root_node_refs",
        set(nodes_by_id),
        "impact_graph.nodes",
    )
    for node in nodes:
        is_root = node.id in root_node_refs
        if is_root and node.impact_state != "root":
            _fail(f"impact_graph.nodes[{node.id!r}].impact_state", "root nodes must use state 'root'")
        if not is_root and node.impact_state == "root":
            _fail(f"impact_graph.nodes[{node.id!r}].impact_state", "only declared root nodes may use state 'root'")

    edges = _load_edges(
        body["edges"],
        node_refs=set(nodes_by_id),
        artifact_refs=declared_artifact_refs,
    )
    _validate_dag(nodes, edges)
    incoming_counts = {node.id: 0 for node in nodes}
    for edge in edges:
        incoming_counts[edge.to_node] += 1
    roots_with_incoming = sorted(
        root_ref for root_ref in root_node_refs if incoming_counts[root_ref] > 0
    )
    if roots_with_incoming:
        _fail(
            "impact_graph.root_node_refs",
            "root nodes must not have incoming edges: " + ", ".join(roots_with_incoming),
        )
    adjacency = _adjacency(nodes, edges)
    reachable = _reachable(root_node_refs, adjacency)
    unreachable = sorted(set(nodes_by_id) - reachable)
    if unreachable:
        _fail("impact_graph.nodes", "all nodes must be reachable from a root: " + ", ".join(unreachable))

    targets = _load_targets(
        body["reevaluation_targets"],
        nodes_by_id=nodes_by_id,
        artifact_refs=declared_artifact_refs,
        adjacency=adjacency,
    )
    blocked_outputs = _string_list(body["blocked_outputs"], "impact_graph.blocked_outputs")
    blocked_actions = _string_list(body["blocked_actions"], "impact_graph.blocked_actions")
    node_index = {(node.kind, node.identity): node for node in nodes}
    for index, output_ref in enumerate(blocked_outputs):
        node = node_index.get(("output", output_ref))
        if node is None or node.impact_state != "blocked":
            _fail(
                f"impact_graph.blocked_outputs[{index}]",
                "requires a matching blocked output node",
            )
    for index, action_ref in enumerate(blocked_actions):
        node = node_index.get(("action", action_ref))
        if node is None or node.impact_state != "blocked":
            _fail(
                f"impact_graph.blocked_actions[{index}]",
                "requires a matching blocked action node",
            )
    blocked_node_outputs = {
        node.identity
        for node in nodes
        if node.kind == "output" and node.impact_state == "blocked"
    }
    blocked_node_actions = {
        node.identity
        for node in nodes
        if node.kind == "action" and node.impact_state == "blocked"
    }
    if blocked_node_outputs != set(blocked_outputs):
        _fail(
            "impact_graph.blocked_outputs",
            "must exactly enumerate all blocked output nodes",
        )
    if blocked_node_actions != set(blocked_actions):
        _fail(
            "impact_graph.blocked_actions",
            "must exactly enumerate all blocked action nodes",
        )

    graph_state = _enum(body["state"], "impact_graph.state", IMPACT_GRAPH_STATES)
    has_unknown = (
        any(node.impact_state == "unknown" for node in nodes)
        or any(edge.state in {"potential", "unknown"} for edge in edges)
        or any(target.state == "unknown" for target in targets)
    )
    has_blocked = bool(blocked_outputs or blocked_actions) or any(
        target.state == "blocked" for target in targets
    )
    if graph_state == "mapped" and (has_unknown or has_blocked):
        _fail("impact_graph.state", "state 'mapped' forbids unknown, potential, or blocked impact")
    if graph_state == "partial" and (not has_unknown or has_blocked):
        _fail("impact_graph.state", "state 'partial' requires unknown/potential impact and forbids blocked targets")
    if graph_state == "blocked" and not has_blocked:
        _fail("impact_graph.state", "state 'blocked' requires a blocked target, output, or action")
    if graph_state == "unknown":
        if has_blocked or not targets or any(target.state != "unknown" for target in targets):
            _fail("impact_graph.state", "state 'unknown' requires all targets unknown and no blocked target")

    return ImpactGraph(
        graph_id=_string(body["graph_id"], "impact_graph.graph_id"),
        recorded_at=recorded_at_text,
        state=graph_state,
        reason=_string(body["reason"], "impact_graph.reason"),
        world_state=world_state,
        artifact_refs=artifact_refs,
        entity_refs=entity_refs,
        root_node_refs=tuple(sorted(root_node_refs)),
        nodes=nodes,
        edges=edges,
        reevaluation_targets=targets,
        blocked_outputs=tuple(sorted(blocked_outputs)),
        blocked_actions=tuple(sorted(blocked_actions)),
    )


def _artifact_sets(
    graph: ImpactGraph,
) -> tuple[dict[str, ImpactArtifactRef], set[str], set[str]]:
    artifacts = {item.ref_id: item for item in graph.artifact_refs}
    discrepancy_refs = {
        ref_id
        for ref_id, item in artifacts.items()
        if item.artifact_id == "geotask.discrepancy-report"
    }
    correction_refs = {
        ref_id
        for ref_id, item in artifacts.items()
        if item.artifact_id == "geotask.correction-request"
    }
    return artifacts, discrepancy_refs, correction_refs


def _resolve_entity_bindings(
    graph: ImpactGraph,
    discrepancy_reports: Mapping[str, DiscrepancyReport],
    correction_requests: Mapping[str, CorrectionRequest],
) -> dict[str, object]:
    resolved: dict[str, object] = {}
    for entity in graph.entity_refs:
        if entity.kind == "discrepancy":
            report = discrepancy_reports[entity.artifact_ref]
            candidates = {item.id: item for item in report.discrepancies}
        else:
            request = correction_requests[entity.artifact_ref]
            if entity.kind == "correction_change":
                candidates = {item.id: item for item in request.changes}
            elif entity.kind == "acceptance_criterion":
                candidates = {item.id: item for item in request.acceptance_criteria}
            else:
                candidates = {item.id: item for item in request.review_requirements}
        if entity.entity_id not in candidates:
            _fail(
                f"impact_graph.entity_refs[{entity.id!r}]",
                f"entity_id {entity.entity_id!r} is absent from bound {entity.artifact_ref!r}",
            )
        resolved[entity.id] = candidates[entity.entity_id]
    return resolved


def _finding_for_change(
    request: CorrectionRequest,
    change: object,
    report_ref: str,
    discrepancy_id: str,
) -> bool:
    discrepancy_ref = next(
        (item for item in request.discrepancy_refs if item.id == change.discrepancy_ref),
        None,
    )
    return bool(
        discrepancy_ref is not None
        and discrepancy_ref.report_ref == report_ref
        and discrepancy_ref.discrepancy_id == discrepancy_id
    )


def _finding_identity_sets(finding: DiscrepancyFinding) -> dict[str, set[str]]:
    return {
        "world_state_path": {finding.subject_path, *finding.impact.affected_paths},
        "assertion": set(finding.impact.affected_assertion_refs),
        "output": set(finding.impact.affected_output_refs),
        "action": set(finding.impact.affected_action_refs),
        "artifact": set(finding.basis_refs),
    }


def validate_impact_graph_bindings(
    graph: ImpactGraph,
    world_state: WorldState,
    discrepancy_reports: Mapping[str, DiscrepancyReport],
    correction_requests: Mapping[str, CorrectionRequest],
    artifact_contents: Mapping[str, bytes],
) -> None:
    """Validate snapshot, exact bytes, source entities, and declared edge semantics.

    This does not discover impact, execute propagation, apply correction, create a
    successor World State, evaluate reevaluation targets, release outputs, or
    authorize actions.
    """

    checks = (
        ("world_state_id", graph.world_state.world_state_id, world_state.world_state_id),
        ("revision", graph.world_state.revision, world_state.revision),
        ("as_of", graph.world_state.as_of, world_state.as_of),
        (
            "semantic_fingerprint",
            graph.world_state.semantic_fingerprint,
            world_state.semantic_fingerprint(),
        ),
    )
    for field, declared, actual in checks:
        if declared != actual:
            _fail(
                f"impact_graph.world_state.{field}",
                f"does not match bound World State: expected {actual!r}",
            )

    artifacts, expected_discrepancy_refs, expected_correction_refs = _artifact_sets(graph)
    if set(discrepancy_reports) != expected_discrepancy_refs:
        _fail("discrepancy_reports", "keys must exactly match bound Discrepancy Report refs")
    if set(correction_requests) != expected_correction_refs:
        _fail("correction_requests", "keys must exactly match bound Correction Request refs")

    recorded_at = _timestamp(graph.recorded_at, "impact_graph.recorded_at")[1]
    for ref_id, report in discrepancy_reports.items():
        ref = artifacts[ref_id]
        if ref.instance_id != report.report_id:
            _fail(f"impact_graph.artifact_refs[{ref_id!r}].instance_id", "does not match report_id")
        report_checks = (
            ("world_state_id", report.world_state.world_state_id, world_state.world_state_id),
            ("revision", report.world_state.revision, world_state.revision),
            ("as_of", report.world_state.as_of, world_state.as_of),
            (
                "semantic_fingerprint",
                report.world_state.semantic_fingerprint,
                world_state.semantic_fingerprint(),
            ),
        )
        for field, declared, actual in report_checks:
            if declared != actual:
                _fail(
                    f"discrepancy_reports[{ref_id!r}].world_state.{field}",
                    f"does not match bound World State: expected {actual!r}",
                )
        if recorded_at < _timestamp(report.recorded_at, f"discrepancy_reports[{ref_id!r}].recorded_at")[1]:
            _fail("impact_graph.recorded_at", f"must not precede report {ref_id!r}")

    for ref_id, request in correction_requests.items():
        ref = artifacts[ref_id]
        if ref.instance_id != request.request_id:
            _fail(f"impact_graph.artifact_refs[{ref_id!r}].instance_id", "does not match request_id")
        request_checks = (
            ("world_state_id", request.base_world_state.world_state_id, world_state.world_state_id),
            ("revision", request.base_world_state.revision, world_state.revision),
            ("as_of", request.base_world_state.as_of, world_state.as_of),
            (
                "semantic_fingerprint",
                request.base_world_state.semantic_fingerprint,
                world_state.semantic_fingerprint(),
            ),
        )
        for field, declared, actual in request_checks:
            if declared != actual:
                _fail(
                    f"correction_requests[{ref_id!r}].base_world_state.{field}",
                    f"does not match bound World State: expected {actual!r}",
                )
        if recorded_at < _timestamp(request.created_at, f"correction_requests[{ref_id!r}].created_at")[1]:
            _fail("impact_graph.recorded_at", f"must not precede request {ref_id!r}")

    expected_contents: dict[str, str] = {
        graph.world_state.ref_id: graph.world_state.content_sha256,
        **{ref_id: ref.content_sha256 for ref_id, ref in artifacts.items()},
    }
    if set(artifact_contents) != set(expected_contents):
        _fail("artifact_contents", "keys must exactly match all declared artifact refs")
    for ref_id, digest in expected_contents.items():
        content = artifact_contents[ref_id]
        if not isinstance(content, bytes):
            _fail(f"artifact_contents[{ref_id!r}]", "must be bytes")
        actual = hashlib.sha256(content).hexdigest()
        if actual != digest:
            _fail(
                f"artifact_contents[{ref_id!r}]",
                f"SHA-256 mismatch: expected {digest!r}, got {actual!r}",
            )

    entities = _resolve_entity_bindings(graph, discrepancy_reports, correction_requests)
    nodes_by_id = {item.id: item for item in graph.nodes}
    entity_by_id = {item.id: item for item in graph.entity_refs}

    path_inventory: set[str] = set()
    assertion_inventory: set[str] = set()
    output_inventory: set[str] = set()
    action_inventory: set[str] = set()
    for report in discrepancy_reports.values():
        for finding in report.discrepancies:
            path_inventory.update({finding.subject_path, *finding.impact.affected_paths})
            path_inventory.update(finding.correction_scope.mutable_paths)
            path_inventory.update(finding.correction_scope.immutable_paths)
            assertion_inventory.update(finding.impact.affected_assertion_refs)
            output_inventory.update(finding.impact.affected_output_refs)
            action_inventory.update(finding.impact.affected_action_refs)
    for request in correction_requests.values():
        path_inventory.update(change.target_path for change in request.changes)
        path_inventory.update(
            criterion.target_path
            for criterion in request.acceptance_criteria
            if criterion.target_path is not None
        )
        path_inventory.update(
            path for review in request.review_requirements for path in review.affected_paths
        )
        output_inventory.update(request.blocked_outputs)
        action_inventory.update(request.blocked_actions)
        output_inventory.update(
            output
            for criterion in request.acceptance_criteria
            for output in criterion.output_refs
        )

    for node in graph.nodes:
        inventory = {
            "world_state_path": path_inventory,
            "assertion": assertion_inventory,
            "output": output_inventory,
            "action": action_inventory,
            "artifact": {graph.world_state.ref_id, *artifacts},
        }.get(node.kind)
        if inventory is not None and node.identity not in inventory:
            _fail(
                f"impact_graph.nodes[{node.id!r}].identity",
                f"is not grounded by bound source Artifacts for node kind {node.kind!r}",
            )

    for edge in graph.edges:
        source = nodes_by_id[edge.from_node]
        target = nodes_by_id[edge.to_node]
        edge_basis = set(edge.basis_refs)
        if not edge_basis.intersection(source.basis_refs):
            _fail(
                f"impact_graph.edges[{edge.id!r}].basis_refs",
                "must include at least one source-node basis ref",
            )
        if not edge_basis.intersection(target.basis_refs):
            _fail(
                f"impact_graph.edges[{edge.id!r}].basis_refs",
                "must include at least one target-node basis ref",
            )
        if edge.state == "confirmed" and (
            source.impact_state == "unknown" or target.impact_state == "unknown"
        ):
            _fail(
                f"impact_graph.edges[{edge.id!r}].state",
                "confirmed edges cannot connect unknown nodes",
            )
        if edge.kind == "changes":
            if source.kind != "correction_change" or target.kind != "world_state_path":
                _fail(f"impact_graph.edges[{edge.id!r}]", "changes requires correction_change -> world_state_path")
            source_entity = entity_by_id[source.entity_ref]
            if source_entity.artifact_ref not in edge_basis:
                _fail(
                    f"impact_graph.edges[{edge.id!r}].basis_refs",
                    "changes edges must include the bound Correction Request ref",
                )
            change = entities[source.entity_ref]
            if change.target_path != target.identity:
                _fail(f"impact_graph.edges[{edge.id!r}]", "target path does not match correction change")
        elif edge.kind == "invalidates":
            if source.kind != "discrepancy":
                _fail(f"impact_graph.edges[{edge.id!r}]", "invalidates requires a discrepancy source")
            source_entity = entity_by_id[source.entity_ref]
            if source_entity.artifact_ref not in edge_basis:
                _fail(
                    f"impact_graph.edges[{edge.id!r}].basis_refs",
                    "invalidates edges must include the bound Discrepancy Report ref",
                )
            finding = entities[source.entity_ref]
            allowed = _finding_identity_sets(finding).get(target.kind, set())
            if target.identity not in allowed:
                _fail(f"impact_graph.edges[{edge.id!r}]", "target is absent from discrepancy subject/impact")
        elif edge.kind == "requires":
            if source.kind == "discrepancy" and target.kind == "correction_change":
                source_entity = entity_by_id[source.entity_ref]
                target_entity = entity_by_id[target.entity_ref]
                required_basis = {
                    source_entity.artifact_ref,
                    target_entity.artifact_ref,
                }
                if not required_basis.issubset(edge_basis):
                    _fail(
                        f"impact_graph.edges[{edge.id!r}].basis_refs",
                        "discrepancy-to-change edges must include both bound source Artifact refs",
                    )
                request = correction_requests[target_entity.artifact_ref]
                change = entities[target.entity_ref]
                if not _finding_for_change(
                    request,
                    change,
                    source_entity.artifact_ref,
                    source_entity.entity_id,
                ):
                    _fail(f"impact_graph.edges[{edge.id!r}]", "correction change is not bound to source discrepancy")
            elif source.kind == "correction_change" and target.kind == "acceptance_criterion":
                source_entity = entity_by_id[source.entity_ref]
                target_entity = entity_by_id[target.entity_ref]
                if source_entity.artifact_ref != target_entity.artifact_ref:
                    _fail(
                        f"impact_graph.edges[{edge.id!r}]",
                        "change and acceptance criterion must come from the same Correction Request",
                    )
                if source_entity.artifact_ref not in edge_basis:
                    _fail(
                        f"impact_graph.edges[{edge.id!r}].basis_refs",
                        "change-to-criterion edges must include the bound Correction Request ref",
                    )
                change = entities[source.entity_ref]
                if target_entity.entity_id not in change.acceptance_criterion_refs:
                    _fail(f"impact_graph.edges[{edge.id!r}]", "acceptance criterion is not required by source change")
            elif source.kind == "review_requirement" and target.kind == "acceptance_criterion":
                source_entity = entity_by_id[source.entity_ref]
                target_entity = entity_by_id[target.entity_ref]
                if source_entity.artifact_ref != target_entity.artifact_ref:
                    _fail(
                        f"impact_graph.edges[{edge.id!r}]",
                        "review requirement and criterion must come from the same Correction Request",
                    )
                if source_entity.artifact_ref not in edge_basis:
                    _fail(
                        f"impact_graph.edges[{edge.id!r}].basis_refs",
                        "review-to-criterion edges must include the bound Correction Request ref",
                    )
                review = entities[source.entity_ref]
                criterion = entities[target.entity_ref]
                if criterion.kind != "human_reviewed" or criterion.reviewer_role != review.reviewer_role:
                    _fail(f"impact_graph.edges[{edge.id!r}]", "review requirement and criterion roles do not match")
            else:
                _fail(f"impact_graph.edges[{edge.id!r}]", "unsupported requires edge shape")
        elif edge.kind == "affects":
            allowed_shapes = {
                "world_state_path": {"world_state_path", "assertion", "output", "action"},
                "assertion": {"output", "action"},
                "output": {"action"},
                "artifact": {"world_state_path", "assertion", "output", "action"},
            }
            if target.kind not in allowed_shapes.get(source.kind, set()):
                _fail(
                    f"impact_graph.edges[{edge.id!r}]",
                    "unsupported affects edge shape",
                )
            inventories = {
                "world_state_path": path_inventory,
                "assertion": assertion_inventory,
                "output": output_inventory,
                "action": action_inventory,
            }
            if target.identity not in inventories[target.kind]:
                _fail(f"impact_graph.edges[{edge.id!r}]", "target is not declared as affected")
        elif edge.kind == "blocks":
            if source.kind not in {"discrepancy", "assertion", "output"}:
                _fail(
                    f"impact_graph.edges[{edge.id!r}]",
                    "blocks requires discrepancy, assertion, or output source",
                )
            if target.kind == "output":
                allowed = output_inventory
            elif target.kind == "action":
                allowed = action_inventory
            else:
                _fail(f"impact_graph.edges[{edge.id!r}]", "blocks must target output or action")
            if target.impact_state != "blocked":
                _fail(
                    f"impact_graph.edges[{edge.id!r}]",
                    "blocks must target a blocked node",
                )
            if target.identity not in allowed:
                _fail(f"impact_graph.edges[{edge.id!r}]", "blocked target is not declared by source Artifacts")
        elif edge.kind == "requires_recheck":
            if source.kind not in {
                "world_state_path",
                "discrepancy",
                "correction_change",
                "artifact",
            }:
                _fail(
                    f"impact_graph.edges[{edge.id!r}]",
                    "requires_recheck source must be a path, discrepancy, correction change, or artifact",
                )
            if target.kind == "assertion":
                allowed = assertion_inventory
            elif target.kind == "output":
                allowed = output_inventory
            else:
                _fail(f"impact_graph.edges[{edge.id!r}]", "requires_recheck must target assertion or output")
            if target.impact_state not in {"requires_recheck", "blocked"}:
                _fail(
                    f"impact_graph.edges[{edge.id!r}]",
                    "requires_recheck must target a requires_recheck or blocked node",
                )
            if target.identity not in allowed:
                _fail(f"impact_graph.edges[{edge.id!r}]", "recheck target is not declared by source Artifacts")
        elif edge.kind == "guards":
            if source.kind != "acceptance_criterion" or target.kind not in {"output", "action"}:
                _fail(f"impact_graph.edges[{edge.id!r}]", "guards requires acceptance_criterion -> output/action")
            source_entity = entity_by_id[source.entity_ref]
            if source_entity.artifact_ref not in edge_basis:
                _fail(
                    f"impact_graph.edges[{edge.id!r}].basis_refs",
                    "guards edges must include the bound Correction Request ref",
                )
            request = correction_requests[source_entity.artifact_ref]
            criterion = entities[source.entity_ref]
            if target.kind == "output" and target.identity not in {
                *criterion.output_refs,
                *request.blocked_outputs,
            }:
                _fail(f"impact_graph.edges[{edge.id!r}]", "output is not guarded by the criterion or request")
            if target.kind == "action" and target.identity not in request.blocked_actions:
                _fail(f"impact_graph.edges[{edge.id!r}]", "action is not guarded by the bound request")


__all__ = [
    "IMPACT_GRAPH_ARTIFACT_ID",
    "IMPACT_GRAPH_SCHEMA_ID",
    "IMPACT_GRAPH_SCHEMA_VERSION",
    "IMPACT_GRAPH_FORMAT_VERSION",
    "IMPACT_GRAPH_STATES",
    "IMPACT_ENTITY_KINDS",
    "IMPACT_NODE_KINDS",
    "IMPACT_NODE_STATES",
    "IMPACT_EDGE_KINDS",
    "IMPACT_EDGE_STATES",
    "REEVALUATION_TARGET_STATES",
    "ImpactGraphFormatError",
    "ImpactArtifactRef",
    "ImpactWorldStateRef",
    "ImpactEntityRef",
    "ImpactNode",
    "ImpactEdge",
    "ReevaluationTarget",
    "ImpactGraph",
    "load_impact_graph",
    "validate_impact_graph_bindings",
]
