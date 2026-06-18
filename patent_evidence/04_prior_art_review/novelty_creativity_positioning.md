# Novelty & Creativity Positioning

## What This Patent Is NOT

This patent is **not** simply:

### ❌ Not Prompt Compression

Conventional prompt compression techniques (e.g., LLMLingua, Selective Context) aim to reduce token count by removing redundant tokens from natural language prompts. They do **not** structurally represent spatial tasks, preserve operator constraints, or enable deterministic verification.

**GeoTask difference**: We define a **task-related spatial encoding** that captures spatial objects, operators, and propositions in a minimal sufficient representation. It is not compression of existing text — it is a structured format that replaces the need for verbose spatial descriptions entirely.

### ❌ Not a Generic LLM-GIS Agent

Existing LLM-GIS agents (e.g., GeoGPT, GIS Copilot) wrap LLMs with GIS tool-calling. They pass natural language to LLMs and let LLMs decide which GIS tools to call.

**GeoTask difference**: We provide **context-gap generation** — the encoding identifies what the LLM needs to know (objects, operators, propositions) and what it does NOT need. The LLM generates **candidate spatial content from model knowledge**, not tool-calling decisions. Verification is **local and deterministic**, not LLM-dependent.

### ❌ Not GIS Workflow Automation

Tools like FME, ArcGIS ModelBuilder, or QGIS Processing Modeler automate GIS workflows with graphical programming.

**GeoTask difference**: GeoTask Core is a **task representation format for LLMs**, not a workflow engine. It defines **object-operator-proposition binding**, allowing LLMs to reason about spatial tasks in a structured way, then have results verified deterministically.

### ❌ Not Site Prospecting

Conventional site prospecting tools optimize location selection based on multi-criteria analysis with GIS data layers.

**GeoTask difference**: GeoTask Core is **domain-agnostic**. It is a lightweight encoding for any spatial task, not tied to any specific domain like site selection. Domain-specific rule packs (e.g., UAV) are separate components.

### ❌ Not Output Format Conversion

Simple format converters (e.g., Markdown → JSON, natural language → structured data) parse output text without spatial domain knowledge.

**GeoTask difference**: GeoTask Normalizer extracts **spatially meaningful** measurements and maps them to deterministic operators. The Verifier **cross-checks model claims against locally computed ground truth**, distinguishing verified, contradicted, and need_review results.

## Key Novelty Points

1. **Task-Related Spatial Encoding** — Encodes spatial tasks with objects, operators, and propositions as first-class entities, not as free-form natural language.

2. **Context Gap Generation** — The encoding defines what the model must know vs. what can be left to model knowledge, enabling efficient LLM input.

3. **Object–Operator–Proposition Binding** — Strucures the relationship between spatial objects, the operations applied to them, and the truth propositions that result.

4. **Deterministic Verification** — Local, LLM-independent verification of model outputs using the same operators defined in the encoding.

5. **Status-Aware Output** — Each measurement is tagged as `verified`, `contradicted`, or `need_review`, providing actionable feedback.

6. **Encoding Template Optimization** — The encoding format is designed to minimize token cost while maximizing verification throughput.
