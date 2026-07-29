# GeoTask Control Expression Language v1.0

Status: implemented public language  
Language identifier: `geotask.control-expression`  
Language version: `1.0`

## 1. Purpose

GeoTask control structures need expressions that can be exchanged, inspected, and validated without executing arbitrary code. The Control Expression Language is a deliberately finite language for:

- `extensions.decision_rule.expression`
- `extensions.evidence_request.resume_when`
- `extensions.evidence_conflict.resume_when`
- `extensions.task_gate.resume_when`

The language is parsed by GeoTask Core when a document declares `geotask.control/1.0`. It is also available through a public parser and evaluator API.

This language is not Python, JavaScript, SQL, or a template language. Implementations MUST NOT interpret control expressions by calling a general-purpose `eval` function.

## 2. Grammar

The normative grammar is:

```text
expression     ::= or_expression
or_expression ::= and_expression (OR and_expression)*
and_expression ::= not_expression (AND not_expression)*
not_expression ::= NOT* comparison
comparison     ::= primary (comparison_operator primary)?
primary        ::= identifier
                 | boolean_literal
                 | unknown_literal
                 | number_literal
                 | string_literal
                 | "(" expression ")"

comparison_operator ::= "==" | "!=" | "<" | "<=" | ">" | ">="
boolean_literal      ::= true | false
unknown_literal      ::= unknown
```

Keywords are ASCII case-insensitive. `AND`, `and`, and `And` are equivalent. Examples SHOULD use uppercase boolean operators and lowercase literals.

## 3. Identifiers

An identifier starts with an ASCII letter or underscore. Remaining characters may contain letters, digits, underscores, dots, or hyphens.

Examples:

```text
route_intersects_zone
vehicle.clearance
source-a-verified
```

A context mapping is resolved in this order:

1. exact top-level key match;
2. dotted mapping traversal.

For example, `vehicle.clearance` resolves from:

```python
{"vehicle": {"clearance": 4.0}}
```

A missing identifier evaluates to `unknown` rather than raising an error.

## 4. Literals

Supported literals are:

- booleans: `true`, `false`;
- unknown value: `unknown`;
- integers: `0`, `15`, `-3`;
- decimal numbers: `6.8`, `-0.5`;
- single- or double-quoted strings: `'verified'`, `"blocked"`.

Supported string escapes are `\n`, `\r`, `\t`, `\\`, `\'`, and `\"`.

Date, time, duration, unit, list, and object literals are not part of v1.0. Applications should provide already-normalized scalar context values.

## 5. Operator precedence

Precedence from highest to lowest is:

1. parenthesized primary expressions;
2. comparison operators;
3. `NOT`;
4. `AND`;
5. `OR`.

Examples:

```text
ready OR authorized AND fresh
```

is interpreted as:

```text
ready OR (authorized AND fresh)
```

A comparison may contain only one comparison operator. Chained comparisons such as `0 < distance < 10` are invalid and must be written as:

```text
distance > 0 AND distance < 10
```

## 6. Three-valued boolean semantics

Boolean operators accept `true`, `false`, or `unknown` and use Kleene-style three-valued logic.

### 6.1 `NOT`

| Input | Result |
|---|---|
| `true` | `false` |
| `false` | `true` |
| `unknown` | `unknown` |

### 6.2 `AND`

| Left | Right | Result |
|---|---|---|
| `false` | any value | `false` |
| `true` | `true` | `true` |
| `true` | `false` | `false` |
| `true` | `unknown` | `unknown` |
| `unknown` | `false` | `false` |
| `unknown` | `true` | `unknown` |
| `unknown` | `unknown` | `unknown` |

### 6.3 `OR`

| Left | Right | Result |
|---|---|---|
| `true` | any value | `true` |
| `false` | `true` | `true` |
| `false` | `false` | `false` |
| `false` | `unknown` | `unknown` |
| `unknown` | `true` | `true` |
| `unknown` | `false` | `unknown` |
| `unknown` | `unknown` | `unknown` |

Non-boolean values cannot be used directly with `NOT`, `AND`, or `OR`. The complete top-level control expression MUST evaluate to `true`, `false`, or `unknown`; a bare number or string is an evaluation error.

## 7. Comparison semantics

If either comparison operand is `unknown`, the result is `unknown`.

`==` and `!=` support:

- boolean with boolean;
- number with number;
- string with string.

Integer and decimal numbers are compatible. Other cross-type equality comparisons are evaluation errors; for example, `true == 1` is not allowed.

`<`, `<=`, `>`, and `>=` require numeric operands. Lexicographic string ordering is intentionally not supported.

Examples:

```text
available_storage_m >= required_storage_m
clearance_evidence_age_seconds <= 15
status == 'verified'
```

## 8. Prohibited syntax

The following are invalid:

```text
function_call()
object.method()
values[0]
a + b
a * b
a = true
a == b == c
```

The language does not provide:

- function or method calls;
- indexing or slicing;
- attribute execution;
- assignment;
- arithmetic;
- list or object construction;
- imports;
- comprehensions;
- regular expressions;
- external I/O.

Dots inside identifiers are mapping-path separators only. They do not provide access to Python object attributes.

## 9. Resource limits

GeoTask Core v1.0 enforces:

- maximum expression length: 4096 characters;
- maximum token count: 1024;
- maximum parenthesis nesting: 64;
- maximum consecutive `NOT` nesting: 64.

Expressions exceeding these limits produce `invalid_expression` diagnostics when validated through `geotask.control/1.0`.

## 10. Public API

```python
from geotask_core import (
    CONTROL_EXPRESSION_LANGUAGE_ID,
    CONTROL_EXPRESSION_LANGUAGE_VERSION,
    parse_control_expression,
    evaluate_control_expression,
    referenced_identifiers,
    ExpressionSyntaxError,
    ExpressionEvaluationError,
)

assert CONTROL_EXPRESSION_LANGUAGE_ID == "geotask.control-expression"
assert CONTROL_EXPRESSION_LANGUAGE_VERSION == "1.0"

expression = parse_control_expression(
    "ground_zone_clear == true AND clearance_age_seconds <= 15"
)

identifiers = referenced_identifiers(expression)
# frozenset({'ground_zone_clear', 'clearance_age_seconds'})

result = evaluate_control_expression(
    expression,
    {
        "ground_zone_clear": True,
        "clearance_age_seconds": 8,
    },
)
# True
```

The evaluator reads only the supplied mapping. It does not mutate context values or perform I/O.

## 11. Validation versus execution

When `geotask.control/1.0` is declared, GeoTask Core validation parses the applicable expression fields. A syntax failure produces:

```text
invalid_expression
```

with the field path and character position.

Successful parsing does not automatically authorize an action. The current public `execute_canonical()` function does not automatically evaluate task gates, unblock outputs, or execute `next_action`. A caller may explicitly evaluate an expression with `evaluate_control_expression()`, while a Runtime or Domain Pack may bind that result to workflow transitions.

Such workflow evaluation MUST NOT be reported as a registered deterministic Core operator unless the corresponding operator contract is implemented and executed.

## 12. JSON Schema boundary

The public JSON Schema enforces that control expressions are non-empty strings no longer than 4096 characters. Full grammar validation is performed by GeoTask Core because JSON Schema regular expressions are not used as a substitute for a parser.

## 13. Versioning

Incompatible grammar or semantic changes require a new language version and, when used by the Control Extension Profile, a compatible Profile revision. Implementations MUST reject unsupported declared Profile versions rather than silently changing expression meaning.
