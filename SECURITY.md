# Security

## No Secrets in Core

GeoTask Core is a pure computation library. It contains no API keys, credentials, tokens, connection strings, or authentication material of any kind. The codebase is safe to clone, audit, and redistribute.

If you discover credentials anywhere in this repository, it is an error. Please report it immediately.

## Reporting Vulnerabilities

If you find a security issue, do not open a public issue. Send details to the maintainers privately. We respond within 72 hours and will confirm receipt.

Security issues include:

- Code paths that could produce incorrect deterministic results (false verification)
- Inputs that cause the parser or validator to produce inconsistent diagnostics
- YAML parsing that could trigger unintended behavior (e.g., arbitrary code execution via unsafe constructors)
- Operator implementations with edge-case bugs that produce wrong values

## Model Execution Boundaries

GeoTask Core does not call any LLM. It does not send data over the network. It does not load model weights. The execution mode `model_only` and the `model` executor type are defined as enums for completeness but have no runtime implementation in Core. They exist as interface placeholders for the private GeoTask Runtime layer.

This means:

- Core cannot leak prompt data to a model provider.
- Core cannot be used as a model proxy or relay.
- Core's output does not depend on any model. Given the same input YAML, it produces the same result every time.

## Deterministic Verification Guarantees

Every operator in Core is a pure function with no side effects:

- `distance_2d`, `point_to_line_distance_2d`: pure math using `math.sqrt`.
- `line_intersects_rect`: computational geometry with no external dependencies.
- `rect_contains_point`: simple bounding-box arithmetic.
- `time_overlap`, `altitude_overlap`: integer or float comparisons.

The verification guarantee: if an assertion is dispatched to a Core operator and the execution returns without error, the computed value is mathematically correct for the declared object data. There is no approximation, no model inference, and no external data source involved.

The assurance level `local_deterministic` (3) means exactly this: the result was computed by a known, deterministic, locally executed function. Higher assurance levels (`model_local_agreement`, `independent_cross_verified`, `human_reviewed`) are the responsibility of the Runtime layer or external verification systems.

## Supply Chain

The only runtime dependency is PyYAML. We pin `pyyaml>=6.0` to avoid known vulnerabilities in earlier versions. We use `yaml.safe_load` exclusively to prevent arbitrary code execution during YAML parsing.

No other packages are imported at runtime. Development dependencies (`pytest`, `matplotlib`) are optional and listed under `[project.optional-dependencies]`.

## Input Safety

- All YAML input is parsed with `yaml.safe_load`. Constructors that execute arbitrary Python code are never used.
- Object IDs and operator names are validated against a strict regex pattern (`^[A-Za-z][A-Za-z0-9_.-]{0,127}$`).
- Numeric inputs are bounded by Python's float range. No arbitrary-precision or unbounded allocation paths exist.
- Document size is not enforced by Core, but downstream systems should impose their own limits before passing documents to Core.
