# GeoTask Core Design Principles

## 1. Core Must Be Light

GeoTask Core is **not** a geospatial platform. It is not a database, a map server,
a routing engine, or a full-stack application.

It is a **format definition** with a **minimal verifiable runtime**.

- The format is human-readable YAML.
- The runtime is a handful of Python functions.
- Dependencies are kept to an absolute minimum (pyyaml, pytest).

If a feature can reasonably live outside Core, it should.

---

## 2. Format and Evaluation Are Separate

- **GeoTask Core**: defines the format and provides basic deterministic operators.
- **GeoTask Eval**: evaluates LLM outputs against Core ground truth.
- **GeoTask Audit**: provides heavy provenance tracking, audit trails, and
  compliance verification.
- **GeoTask UAV**: provides domain-specific rule packs and object libraries for
  unmanned aerial vehicle operations.

The Core does not depend on any of these. They depend on the Core.

---

## 3. General-Purpose First, Scene Extension Later

Core objects (point, line, rect) and Core operators (distance_2d,
line_intersects_rect) are chosen for their **universal applicability**.

Domain-specific objects (no-fly zones, flight corridors, terrain grids) and
domain-specific operators (obstacle clearance, altitude validation) belong in
domain-specific rule packs, not in Core.

---

## 4. LLM-Friendly First

Every design decision in Core is evaluated against:

> "Can an LLM read this format and produce a reasonable response?"

- Field names are descriptive English.
- Coordinates are simple arrays.
- Operators have formula strings for context.
- The format is self-documenting.

---

## 5. Incrementally Enhanceable

Core v0.1-lite is intentionally minimal. Future versions may add:

- 3D coordinates
- Multi-segment polylines
- Polygon objects
- Additional deterministic operators
- Task chaining

But each addition must pass the "lightweight test": can it be added without
breaking the simple model that makes Core useful?

---

## 6. GeoTask Does Not Replace GeoJSON

GeoJSON is a data interchange format for geographic features. GeoTask is a task
representation format that includes objects, operations, questions, and
verification. They serve different purposes and are complementary.

## 7. GeoTask Is Not a Drone System

GeoTask Core is a general-purpose spatial task representation. While it can be
extended with domain-specific rule packs (such as GeoTask UAV), the Core itself
is domain-agnostic.
