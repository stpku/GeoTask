# GeoTask Core Open Source Boundary

## What Is Open Source (This Repository)

The following components are released under the MIT License:

| Component              | Description                                       |
|------------------------|---------------------------------------------------|
| GeoTask Core format spec | YAML schema and field definitions               |
| Example documents      | Sample GeoTask Core YAML files                    |
| Core parser            | YAML loading and validation                       |
| Core operators         | Deterministic 6 spatial operators                 |
| Core runner            | Auto-detection and execution of spatial tasks     |
| Core normalizer        | Multi-operator extraction (Chinese/English/YAML/Markdown) |
| Core verifier          | Deterministic verification with unified status hierarchy |
| Simple evaluator       | Comparison of LLM output against Core ground truth |
| CLI                    | validate, run, normalize, eval commands           |
| Runtime SDK contracts  | Interface definitions (Protocols, dataclasses) — reference only |
| Mock runtime           | Deterministic mock pipeline — demonstration only  |

These components are sufficient for:

- Understanding the GeoTask format
- Building GeoTask-compatible tools
- Evaluating LLM spatial reasoning
- Academic research on spatial task representation

---

## What Is NOT Open Source

The following components are **not** included in this repository
and are **not** covered by the MIT License:

| Component                   | Status          |
|-----------------------------|-----------------|
| Full GeoTask Runtime        | Proprietary     |
| Domain Packs (industry rules) | Proprietary     |
| Real-world data connectors  | Proprietary     |
| Audit / review backend      | Proprietary     |
| Customer case studies       | Proprietary     |
| Failure sample library      | Proprietary     |
| Encoding planner (production) | Proprietary     |
| Model routing policy (production) | Proprietary   |
| Cost control and governance | Proprietary     |
| Industry scoring models     | Proprietary     |

---

## Why This Boundary Exists

GeoTask Core is the **format**. It defines how spatial tasks are expressed
for LLMs. The business logic -- domain-specific rules, data pipelines, audit
trails, and production infrastructure -- is separate and not part of the
open source release.

This separation:

1. **Keeps Core light.** No database drivers, no API gateways, no complex
   deployment configs.
2. **Protects commercial value.** The heavy engineering is in the platform,
   not the format.
3. **Encourages adoption.** Anyone can build tools that read/write GeoTask
   without licensing friction.
4. **Prevents confusion.** Users know exactly what they get and what they
   don't.

---

## Using GeoTask Core

If you build a tool that reads or writes GeoTask Core format:

- You are welcome to use the open source parser and operators.
- You may extend the format with your own object types and operators.
- You do not need to open source your extensions.

Attribution is appreciated but not required by the MIT License.

---

## See Also

- [`open_core_commercial_runtime_boundary.md`](open_core_commercial_runtime_boundary.md) — Detailed Core/Runtime/Domain Pack boundary with open vs. private classification
- [`product_architecture_v0_1.md`](product_architecture_v0_1.md) — Full product architecture with Mermaid diagrams
- [`patent_boundary.md`](patent_boundary.md) — Patent rights and open source interaction
