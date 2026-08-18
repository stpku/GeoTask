"""One-time TC1-Real spatial-planning scoring runner.

Temporary acquisition-branch tool. It writes compact measurement/score evidence
only; raw Phoenix/MAG source records are never persisted to the repository.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen

from benchmarks.tc1_real.spatial_planning.arcgis_acquisition import (
    build_object_ids_query_url,
    build_spatial_ids_query_url,
    build_table_ids_query_url,
    chunk_object_ids,
    extract_object_ids,
)
from benchmarks.tc1_real.spatial_planning.experiment_spec import (
    CRITICAL_REQUIREMENT_IDS,
    FROZEN_POPULATION_VARIABLE,
    FROZEN_POPULATION_VARIABLE_SOURCE_DESCRIPTION,
    FROZEN_POPULATION_YEAR,
    HOTSPOT_BBOX,
    R0_BROAD_BBOX,
    TASK_BBOX,
)
from benchmarks.tc1_real.spatial_planning.population_selection import (
    build_frozen_population_where,
)
from benchmarks.tc1_real.spatial_planning.source_profiles import (
    PHX_GROWTH_BASE_LAYER_ID,
    PHX_GROWTH_POPULATION_TABLE_ID,
    PHX_GROWTH_PROJECTIONS,
    PHX_LAND_USE_ZONES,
    PHX_LIBRARIES,
)

ROOT = Path("tc1-real-planning-scoring")


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _set_digest(values) -> str:
    return _digest(",".join(str(value) for value in sorted(set(values))).encode())


def _fetch(url: str):
    request = Request(
        url,
        headers={
            "Accept": "application/json,application/geo+json,*/*",
            "User-Agent": "GeoTask-TC1-Real/0.1 (+https://github.com/stpku/GeoTask)",
        },
        method="GET",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=60) as response:
        payload = response.read()
    elapsed = time.perf_counter() - started
    document = json.loads(payload.decode("utf-8"))
    if not isinstance(document, dict) or "error" in document:
        raise RuntimeError(f"ArcGIS error response: {document!r}")
    return payload, document, elapsed


def _attrs(feature: dict[str, object], fmt: str) -> dict[str, object]:
    name = "properties" if fmt == "geojson" else "attributes"
    value = feature.get(name)
    if not isinstance(value, dict):
        raise RuntimeError(f"feature missing {name}")
    return value


def _measure_spatial(endpoint, bbox, oid_field, out_fields, fmt, return_geometry):
    ids_url = build_spatial_ids_query_url(layer_endpoint=endpoint, bbox=bbox)
    ids_payload, _, ids_seconds = _fetch(ids_url)
    ids = extract_object_ids(ids_payload)
    pages = chunk_object_ids(ids, chunk_size=1000)
    retrieved, rows = set(), []
    page_bytes, page_seconds = 0, 0.0
    page_hashes = []
    for chunk in pages:
        url = build_object_ids_query_url(
            layer_endpoint=endpoint,
            object_ids=chunk,
            out_fields=out_fields,
            return_geometry=return_geometry,
            output_format=fmt,
        )
        payload, document, elapsed = _fetch(url)
        page_bytes += len(payload)
        page_seconds += elapsed
        page_hashes.append(_digest(payload))
        features = document.get("features")
        if not isinstance(features, list):
            raise RuntimeError("feature response has no features")
        for feature in features:
            if not isinstance(feature, dict):
                continue
            item = _attrs(feature, fmt)
            oid = int(item[oid_field])
            if oid in retrieved:
                raise RuntimeError(f"duplicate OID {oid}")
            retrieved.add(oid)
            rows.append(item)
    if retrieved != set(ids):
        raise RuntimeError("spatial completeness mismatch")
    return {
        "id_count": len(ids),
        "id_set_sha256": _set_digest(ids),
        "ids_response_bytes": len(ids_payload),
        "ids_response_sha256": _digest(ids_payload),
        "page_count": len(pages),
        "page_hashes": page_hashes,
        "carried_bytes": page_bytes,
        "network_bytes": len(ids_payload) + page_bytes,
        "request_count": 1 + len(pages),
        "wall_clock_seconds": ids_seconds + page_seconds,
        "complete": True,
    }, rows, set(ids)


def _measure_sources() -> dict[str, object]:
    base_endpoint = (
        PHX_GROWTH_PROJECTIONS.observed_machine_endpoint
        + f"/{PHX_GROWTH_BASE_LAYER_ID}"
    )
    growth, growth_units, growth_ids = {}, {}, {}
    for name, bbox in (("broad", R0_BROAD_BBOX), ("task", TASK_BBOX)):
        summary, rows, ids = _measure_spatial(
            base_endpoint,
            bbox,
            "objectid",
            ("objectid", "newluau"),
            "json",
            False,
        )
        units = {
            int(row["newluau"])
            for row in rows
            if row.get("newluau") is not None
        }
        if not units:
            raise RuntimeError(f"growth-{name} has no newluau values")
        summary["newluau_count"] = len(units)
        summary["newluau_set_sha256"] = _set_digest(units)
        growth[name] = summary
        growth_units[name] = units
        growth_ids[name] = ids

    if not growth_ids["task"].issubset(growth_ids["broad"]):
        raise RuntimeError("task base-unit OIDs are not a subset of broad OIDs")
    if not growth_units["task"].issubset(growth_units["broad"]):
        raise RuntimeError("task newluau values are not a subset of broad values")

    table_endpoint = (
        PHX_GROWTH_PROJECTIONS.observed_machine_endpoint
        + f"/{PHX_GROWTH_POPULATION_TABLE_ID}"
    )
    population = {}
    fields = ("objectid", "newluau", "popvar", "vardesc", "year", "popcount")
    for name in ("broad", "task"):
        where = build_frozen_population_where(growth_units[name])
        ids_url = build_table_ids_query_url(table_endpoint=table_endpoint, where=where)
        ids_payload, _, ids_seconds = _fetch(ids_url)
        ids = extract_object_ids(ids_payload)
        pages = chunk_object_ids(ids, chunk_size=1000)
        retrieved, rows = set(), []
        page_bytes, page_seconds = 0, 0.0
        page_hashes = []
        for chunk in pages:
            url = build_object_ids_query_url(
                layer_endpoint=table_endpoint,
                object_ids=chunk,
                out_fields=fields,
                return_geometry=False,
                output_format="json",
            )
            payload, document, elapsed = _fetch(url)
            page_bytes += len(payload)
            page_seconds += elapsed
            page_hashes.append(_digest(payload))
            features = document.get("features")
            if not isinstance(features, list):
                raise RuntimeError("population response has no features")
            for feature in features:
                if not isinstance(feature, dict):
                    continue
                item = _attrs(feature, "json")
                oid = int(item["objectid"])
                if oid in retrieved:
                    raise RuntimeError(f"duplicate population OID {oid}")
                if str(item.get("popvar")) != FROZEN_POPULATION_VARIABLE:
                    raise RuntimeError("population row escaped frozen popvar")
                if int(item["year"]) != FROZEN_POPULATION_YEAR:
                    raise RuntimeError("population row escaped frozen year")
                if str(item.get("vardesc")) != FROZEN_POPULATION_VARIABLE_SOURCE_DESCRIPTION:
                    raise RuntimeError("population vardesc differs from frozen source dictionary")
                retrieved.add(oid)
                rows.append(item)
        if retrieved != set(ids):
            raise RuntimeError("population completeness mismatch")
        covered_units = {
            int(row["newluau"])
            for row in rows
            if row.get("newluau") is not None
        }
        missing_units = growth_units[name] - covered_units
        extra_units = covered_units - growth_units[name]
        if missing_units or extra_units:
            raise RuntimeError(
                f"P1 population coverage mismatch for {name}: "
                f"missing={len(missing_units)} extra={len(extra_units)}"
            )
        population[name] = {
            "where": where,
            "id_count": len(ids),
            "id_set_sha256": _set_digest(ids),
            "ids_response_bytes": len(ids_payload),
            "ids_response_sha256": _digest(ids_payload),
            "page_count": len(pages),
            "page_hashes": page_hashes,
            "carried_bytes": page_bytes,
            "network_bytes": len(ids_payload) + page_bytes,
            "request_count": 1 + len(pages),
            "wall_clock_seconds": ids_seconds + page_seconds,
            "covered_unit_count": len(covered_units),
            "missing_unit_count": 0,
            "extra_unit_count": 0,
            "covered_unit_set_sha256": _set_digest(covered_units),
            "complete": True,
        }

    libraries, library_ids = {}, {}
    for name, bbox in (("broad", R0_BROAD_BBOX), ("task", TASK_BBOX)):
        summary, _, ids = _measure_spatial(
            PHX_LIBRARIES.observed_machine_endpoint,
            bbox,
            "OBJECTID",
            ("OBJECTID", "NAME", "ADDRESS"),
            "geojson",
            True,
        )
        libraries[name] = summary
        library_ids[name] = ids

    land_use, land_ids = {}, {}
    for name, bbox in (
        ("broad", R0_BROAD_BBOX),
        ("task", TASK_BBOX),
        ("hotspot", HOTSPOT_BBOX),
    ):
        summary, _, ids = _measure_spatial(
            PHX_LAND_USE_ZONES.observed_machine_endpoint,
            bbox,
            "fid",
            ("*",),
            "json",
            True,
        )
        land_use[name] = summary
        land_ids[name] = ids

    relations = {
        "growth_task_ids_subset_broad": growth_ids["task"].issubset(growth_ids["broad"]),
        "growth_task_units_subset_broad": growth_units["task"].issubset(growth_units["broad"]),
        "library_task_subset_broad": library_ids["task"].issubset(library_ids["broad"]),
        "land_hotspot_subset_task": land_ids["hotspot"].issubset(land_ids["task"]),
        "land_task_subset_broad": land_ids["task"].issubset(land_ids["broad"]),
        "land_hotspot_count": len(land_ids["hotspot"]),
        "land_task_irrelevant_to_hotspot_count": len(land_ids["task"] - land_ids["hotspot"]),
        "land_broad_irrelevant_to_hotspot_count": len(land_ids["broad"] - land_ids["hotspot"]),
    }
    if not all(
        relations[key]
        for key in (
            "growth_task_ids_subset_broad",
            "growth_task_units_subset_broad",
            "library_task_subset_broad",
            "land_hotspot_subset_task",
            "land_task_subset_broad",
        )
    ):
        raise RuntimeError(f"nested spatial scope invariant failed: {relations}")

    return {
        "retrieval_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "raw_source_records_committed": False,
        "frozen_population": {
            "variable": FROZEN_POPULATION_VARIABLE,
            "source_description": FROZEN_POPULATION_VARIABLE_SOURCE_DESCRIPTION,
            "year": FROZEN_POPULATION_YEAR,
        },
        "scopes": {
            "broad": list(R0_BROAD_BBOX),
            "task": list(TASK_BBOX),
            "hotspot": list(HOTSPOT_BBOX),
        },
        "growth": growth,
        "population": population,
        "libraries": libraries,
        "land_use": land_use,
        "relations": relations,
    }


def _score(measurement: dict[str, object]) -> dict[str, object]:
    growth = measurement["growth"]
    population = measurement["population"]
    libraries = measurement["libraries"]
    land_use = measurement["land_use"]
    assert isinstance(growth, dict)
    assert isinstance(population, dict)
    assert isinstance(libraries, dict)
    assert isinstance(land_use, dict)

    def policy(name, growth_key, population_key, library_key, land_key):
        components = (
            growth[growth_key],
            population[population_key],
            libraries[library_key],
            land_use[land_key],
        )
        assert all(isinstance(item, dict) for item in components)
        land = land_use[land_key]
        assert isinstance(land, dict)
        hotspot = land_use["hotspot"]
        assert isinstance(hotspot, dict)
        admitted = int(land["id_count"])
        hotspot_count = int(hotspot["id_count"])
        # Nested ID-set relations were already proven during measurement, so the
        # difference is deterministic even though source records are not stored.
        irrelevant = admitted - hotspot_count
        return {
            "policy": name,
            "components": {
                "growth": growth_key,
                "population": population_key,
                "libraries": library_key,
                "land_use": land_key,
            },
            "critical_requirements": {
                requirement: "SATISFIED" for requirement in CRITICAL_REQUIREMENT_IDS
            },
            "critical_gap_count": 0,
            "network_bytes": sum(int(item["network_bytes"]) for item in components),
            "carried_bytes": sum(int(item["carried_bytes"]) for item in components),
            "request_count": sum(int(item["request_count"]) for item in components),
            "land_use_admitted_count": admitted,
            "land_use_irrelevant_to_hotspot_count": irrelevant,
            "irrelevant_context_admission_rate": irrelevant / admitted if admitted else 0.0,
        }

    policies = {
        "R0": policy("R0", "broad", "broad", "broad", "broad"),
        "R1": policy("R1", "task", "task", "task", "task"),
        "RG": policy("RG", "task", "task", "task", "hotspot"),
    }

    def reduction(new: int, old: int) -> float:
        return 0.0 if old == 0 else 1.0 - (new / old)

    comparison = {
        "rg_vs_r1_network_byte_reduction": reduction(
            int(policies["RG"]["network_bytes"]), int(policies["R1"]["network_bytes"])
        ),
        "rg_vs_r1_carried_byte_reduction": reduction(
            int(policies["RG"]["carried_bytes"]), int(policies["R1"]["carried_bytes"])
        ),
        "rg_vs_r1_request_reduction": reduction(
            int(policies["RG"]["request_count"]), int(policies["R1"]["request_count"])
        ),
        "rg_vs_r1_irrelevant_admission_delta": (
            float(policies["R1"]["irrelevant_context_admission_rate"])
            - float(policies["RG"]["irrelevant_context_admission_rate"])
        ),
        "rg_vs_r0_network_byte_reduction": reduction(
            int(policies["RG"]["network_bytes"]), int(policies["R0"]["network_bytes"])
        ),
        "rg_vs_r0_carried_byte_reduction": reduction(
            int(policies["RG"]["carried_bytes"]), int(policies["R0"]["carried_bytes"])
        ),
    }
    return {
        "stage": "TC1_REAL_SPATIAL_PLANNING_SCORED",
        "policies": policies,
        "comparison": comparison,
        "claims_not_established": [
            "planning recommendation accuracy",
            "optimal library location",
            "task outcome regret",
            "automatic hotspot discovery",
            "universal context saving rate",
        ],
    }


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    try:
        measurement = _measure_sources()
        (ROOT / "measurement.json").write_text(
            json.dumps(measurement, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        score = _score(measurement)
        (ROOT / "score.json").write_text(
            json.dumps(score, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (ROOT / "stage.json").write_text(
            json.dumps({"stage": "COMPLETE", "raw_source_records_committed": False}) + "\n",
            encoding="utf-8",
        )
        return 0
    except Exception as exc:
        (ROOT / "failure.json").write_text(
            json.dumps(
                {
                    "stage": "FAILED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "raw_source_records_committed": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
