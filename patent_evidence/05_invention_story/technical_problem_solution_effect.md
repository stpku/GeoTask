# Technical Problem → Solution → Effect

## 1. Technical Problem (要解决的技术问题)

### P1: High Token Cost from Redundant Spatial Context

When spatial tasks are described in natural language for LLMs, the input contains significant redundancy. Spatial coordinates, object relationships, and operation definitions are embedded in verbose text, inflating token consumption without adding information value.

### P2: Insufficient Local Spatial Data and GIS Operators

LLMs lack access to local spatial datasets and deterministic GIS operators. They cannot compute precise distances, intersections, or spatial relationships — they can only approximate based on training data patterns.

### P3: Unstable LLM Output Format

LLM outputs vary in structure, language, and precision. The same spatial question can yield different formatting across calls, making downstream programmatic consumption unreliable.

### P4: Potential LLM Spatial Calculation Errors

LLMs may produce incorrect spatial calculations (wrong distances, incorrect boolean judgments) while appearing confident. Without deterministic verification, these errors propagate into downstream systems.

### P5: Difficulty Integrating Results into Business Systems

Unstructured LLM outputs are hard to integrate into GIS pipelines, audit systems, or automated workflows that require structured, verifiable results.

## 2. Technical Solution (技术方案)

### S1: Task-Related Spatial Encoding

Define a lightweight encoding format (GeoTask YAML / Compact DSL) that represents spatial objects, operators, and tasks as structured, machine-readable primitives. This replaces verbose natural language descriptions with minimal sufficient representations.

### S2: Minimal Sufficient Spatial Task Representation

The encoding captures only what the LLM needs: object locations, operator definitions, and task questions. Redundant context (coordinate system explanations, formatting instructions) is eliminated.

### S3: Context Gap Generation

The encoding explicitly defines the boundary between "provided context" and "model knowledge." The LLM generates candidate spatial content (measurements, judgments) from its understanding, while the system provides the spatial ground truth for verification.

### S4: Model Knowledge-Enhanced Generation

The encoding enables LLMs to leverage their training knowledge for spatial reasoning while constraining them within the defined task structure. The LLM fills context gaps with candidate answers rather than free-form generation.

### S5: Object–Operator–Proposition Binding

Each spatial task binds objects (points, lines, rectangles) to operators (distance_2d, line_intersects_rect) and produces propositions (distance value, intersection boolean). This three-way binding creates a verifiable claim structure.

### S6: Normalizer

The Normalizer extracts structured measurements from unstructured LLM text output, mapping natural language values to typed GeoTask measurements with operator references.

### S7: Verifier

The Verifier cross-checks normalized model claims against locally computed deterministic results, producing status tags: `verified`, `contradicted`, or `need_review`.

### S8: Status-Aware Output

Each measurement carries a verification status, expected ground truth value, and difference (for numeric values). Contradicted results and missing operator references are flagged for human review.

## 3. Technical Effect (技术效果)

### E1: Reduced Token Input Cost

Task-related spatial encoding reduces input token count by 60-80% compared to equivalent natural language descriptions (demonstrated in Encoding Benchmark v0.1).

### E2: Improved Normalization Success Rate

Structured encodings (GeoTask YAML, Compact DSL) produce more consistently extractable model outputs, increasing normalization success rates.

### E3: Improved Verifiable Result Ratio

By binding objects to operators and propositions, more model outputs can be deterministically verified, reducing the proportion of unverifiable results.

### E4: Model Error Detection

The Verifier identifies contradicted outputs (wrong distances, incorrect boolean judgments), preventing silent error propagation into downstream systems.

### E5: Graceful Degradation to need_data / need_review

When model outputs lack sufficient information (missing operators, ambiguous values), the system converts them to `need_review` status rather than treating them as valid or silently failing.

### E6: Encoding Template Optimization

The encoding format can be tuned for token efficiency while maintaining verification capability, as demonstrated by the Compact DSL achieving the highest benchmark scores with the lowest token cost.
