"""Safe parser and evaluator for GeoTask control expressions.

The language is deliberately small. It supports identifiers, scalar literals,
parentheses, boolean operators, and scalar comparisons. It never delegates to
Python ``eval`` and does not permit calls, indexing, arithmetic, assignment, or
attribute execution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping


class ExpressionSyntaxError(ValueError):
    """Raised when a control expression does not match the finite grammar."""

    def __init__(self, message: str, position: int) -> None:
        super().__init__(f"{message} at position {position}")
        self.message = message
        self.position = position


class ExpressionEvaluationError(ValueError):
    """Raised when a syntactically valid expression uses incompatible values."""


@dataclass(frozen=True)
class LiteralExpression:
    value: bool | int | float | str | None


@dataclass(frozen=True)
class IdentifierExpression:
    name: str


@dataclass(frozen=True)
class UnaryExpression:
    operator: str
    operand: "ControlExpression"


@dataclass(frozen=True)
class BinaryExpression:
    operator: str
    left: "ControlExpression"
    right: "ControlExpression"


ControlExpression = (
    LiteralExpression
    | IdentifierExpression
    | UnaryExpression
    | BinaryExpression
)


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str
    position: int


CONTROL_EXPRESSION_LANGUAGE_ID = "geotask.control-expression"
CONTROL_EXPRESSION_LANGUAGE_VERSION = "1.0"
MAX_EXPRESSION_LENGTH = 4096
MAX_EXPRESSION_TOKENS = 1024
MAX_EXPRESSION_DEPTH = 64

_COMPARISON_OPERATORS = {"==", "!=", "<", "<=", ">", ">="}
_KEYWORDS = {"AND", "OR", "NOT", "TRUE", "FALSE", "UNKNOWN"}


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    index = 0
    length = len(text)
    nesting_depth = 0

    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue

        if text.startswith(("==", "!=", "<=", ">="), index):
            tokens.append(_Token("OP", text[index : index + 2], index))
            index += 2
            continue

        if char in "<>()":
            if char == "(":
                nesting_depth += 1
                if nesting_depth > MAX_EXPRESSION_DEPTH:
                    raise ExpressionSyntaxError(
                        f"Expression nesting exceeds {MAX_EXPRESSION_DEPTH}",
                        index,
                    )
            elif char == ")":
                nesting_depth -= 1
            kind = "LPAREN" if char == "(" else "RPAREN" if char == ")" else "OP"
            tokens.append(_Token(kind, char, index))
            index += 1
            continue

        if char in {'"', "'"}:
            quote = char
            start = index
            index += 1
            value_chars: list[str] = []
            while index < length:
                current = text[index]
                if current == quote:
                    index += 1
                    tokens.append(_Token("STRING", "".join(value_chars), start))
                    break
                if current == "\\":
                    index += 1
                    if index >= length:
                        raise ExpressionSyntaxError("Unterminated string escape", start)
                    escaped = text[index]
                    escapes = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"', "'": "'"}
                    if escaped not in escapes:
                        raise ExpressionSyntaxError(
                            f"Unsupported string escape '\\{escaped}'",
                            index - 1,
                        )
                    value_chars.append(escapes[escaped])
                    index += 1
                    continue
                value_chars.append(current)
                index += 1
            else:
                raise ExpressionSyntaxError("Unterminated string literal", start)
            continue

        if char.isdigit() or (char == "-" and index + 1 < length and text[index + 1].isdigit()):
            start = index
            if char == "-":
                index += 1
            while index < length and text[index].isdigit():
                index += 1
            if index < length and text[index] == ".":
                index += 1
                decimal_start = index
                while index < length and text[index].isdigit():
                    index += 1
                if index == decimal_start:
                    raise ExpressionSyntaxError("Expected digits after decimal point", index)
            tokens.append(_Token("NUMBER", text[start:index], start))
            continue

        if char.isalpha() or char == "_":
            start = index
            index += 1
            while index < length and (
                text[index].isalnum() or text[index] in "_.-"
            ):
                index += 1
            value = text[start:index]
            upper = value.upper()
            if upper in _KEYWORDS:
                tokens.append(_Token(upper, upper, start))
            else:
                tokens.append(_Token("IDENTIFIER", value, start))
            continue

        raise ExpressionSyntaxError(f"Unsupported character {char!r}", index)

    tokens.append(_Token("EOF", "", length))
    return tokens


class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self.tokens = tokens
        self.index = 0

    @property
    def current(self) -> _Token:
        return self.tokens[self.index]

    def advance(self) -> _Token:
        token = self.current
        self.index += 1
        return token

    def match(self, *kinds: str) -> _Token | None:
        if self.current.kind in kinds:
            return self.advance()
        return None

    def expect(self, kind: str, message: str) -> _Token:
        token = self.match(kind)
        if token is None:
            raise ExpressionSyntaxError(message, self.current.position)
        return token

    def parse(self) -> ControlExpression:
        expression = self.parse_or()
        if self.current.kind != "EOF":
            if self.current.kind == "LPAREN":
                message = "Function calls are not allowed"
            elif self.current.kind == "OP" and self.current.value in _COMPARISON_OPERATORS:
                message = "Chained comparisons are not allowed"
            else:
                message = f"Unexpected token {self.current.value!r}"
            raise ExpressionSyntaxError(message, self.current.position)
        return expression

    def parse_or(self) -> ControlExpression:
        expression = self.parse_and()
        while self.match("OR"):
            expression = BinaryExpression("OR", expression, self.parse_and())
        return expression

    def parse_and(self) -> ControlExpression:
        expression = self.parse_not()
        while self.match("AND"):
            expression = BinaryExpression("AND", expression, self.parse_not())
        return expression

    def parse_not(self) -> ControlExpression:
        operator_count = 0
        while self.match("NOT"):
            operator_count += 1
            if operator_count > MAX_EXPRESSION_DEPTH:
                raise ExpressionSyntaxError(
                    f"Unary nesting exceeds {MAX_EXPRESSION_DEPTH}",
                    self.current.position,
                )
        expression = self.parse_comparison()
        for _ in range(operator_count):
            expression = UnaryExpression("NOT", expression)
        return expression

    def parse_comparison(self) -> ControlExpression:
        expression = self.parse_primary()
        if self.current.kind == "OP" and self.current.value in _COMPARISON_OPERATORS:
            operator = self.advance().value
            right = self.parse_primary()
            expression = BinaryExpression(operator, expression, right)
        return expression

    def parse_primary(self) -> ControlExpression:
        token = self.current
        if self.match("LPAREN"):
            expression = self.parse_or()
            self.expect("RPAREN", "Expected ')' to close expression")
            return expression
        if self.match("TRUE"):
            return LiteralExpression(True)
        if self.match("FALSE"):
            return LiteralExpression(False)
        if self.match("UNKNOWN"):
            return LiteralExpression(None)
        if self.match("NUMBER"):
            value: int | float
            value = float(token.value) if "." in token.value else int(token.value)
            return LiteralExpression(value)
        if self.match("STRING"):
            return LiteralExpression(token.value)
        if self.match("IDENTIFIER"):
            return IdentifierExpression(token.value)
        if token.kind == "EOF":
            raise ExpressionSyntaxError("Expected an expression", token.position)
        raise ExpressionSyntaxError(f"Unexpected token {token.value!r}", token.position)


def parse_control_expression(text: str) -> ControlExpression:
    """Parse *text* into a safe immutable expression tree."""

    if not isinstance(text, str):
        raise TypeError("control expression must be a string")
    if not text.strip():
        raise ExpressionSyntaxError("Expression is empty", 0)
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise ExpressionSyntaxError(
            f"Expression length exceeds {MAX_EXPRESSION_LENGTH}",
            MAX_EXPRESSION_LENGTH,
        )

    tokens = _tokenize(text)
    if len(tokens) - 1 > MAX_EXPRESSION_TOKENS:
        raise ExpressionSyntaxError(
            f"Expression token count exceeds {MAX_EXPRESSION_TOKENS}",
            tokens[MAX_EXPRESSION_TOKENS].position,
        )
    return _Parser(tokens).parse()


def referenced_identifiers(expression: str | ControlExpression) -> frozenset[str]:
    """Return all identifier names referenced by an expression."""

    node = parse_control_expression(expression) if isinstance(expression, str) else expression
    names: set[str] = set()

    def visit(current: ControlExpression) -> None:
        if isinstance(current, IdentifierExpression):
            names.add(current.name)
        elif isinstance(current, UnaryExpression):
            visit(current.operand)
        elif isinstance(current, BinaryExpression):
            visit(current.left)
            visit(current.right)

    visit(node)
    return frozenset(names)


def _resolve_identifier(context: Mapping[str, object], name: str) -> object:
    if name in context:
        return context[name]

    current: object = context
    for part in name.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _as_truth_value(value: object, operator: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ExpressionEvaluationError(
        f"Operator {operator} requires boolean or unknown operands, got {type(value).__name__}"
    )


def _is_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return not isinstance(value, float) or math.isfinite(value)


def _evaluate_comparison(operator: str, left: object, right: object) -> bool | None:
    if left is None or right is None:
        return None

    if operator in {"==", "!="}:
        compatible = (
            type(left) is type(right)
            or (_is_number(left) and _is_number(right))
        )
        if not compatible:
            raise ExpressionEvaluationError(
                f"Cannot compare {type(left).__name__} and {type(right).__name__} with {operator}"
            )
        result = left == right
        return result if operator == "==" else not result

    if not (_is_number(left) and _is_number(right)):
        raise ExpressionEvaluationError(
            f"Operator {operator} requires numeric operands"
        )

    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    raise ExpressionEvaluationError(f"Unsupported comparison operator {operator}")


def evaluate_control_expression(
    expression: str | ControlExpression,
    context: Mapping[str, object],
) -> bool | None:
    """Evaluate a finite control expression against a read-only mapping.

    Missing identifiers resolve to ``None`` (unknown). Boolean operators use
    Kleene-style three-valued logic. Comparisons with an unknown operand also
    return unknown.
    """

    node = parse_control_expression(expression) if isinstance(expression, str) else expression

    def evaluate(current: ControlExpression) -> object:
        if isinstance(current, LiteralExpression):
            return current.value
        if isinstance(current, IdentifierExpression):
            return _resolve_identifier(context, current.name)
        if isinstance(current, UnaryExpression):
            value = _as_truth_value(evaluate(current.operand), current.operator)
            return None if value is None else not value
        if isinstance(current, BinaryExpression):
            if current.operator == "AND":
                left = _as_truth_value(evaluate(current.left), "AND")
                if left is False:
                    return False
                right = _as_truth_value(evaluate(current.right), "AND")
                if right is False:
                    return False
                if left is None or right is None:
                    return None
                return True
            if current.operator == "OR":
                left = _as_truth_value(evaluate(current.left), "OR")
                if left is True:
                    return True
                right = _as_truth_value(evaluate(current.right), "OR")
                if right is True:
                    return True
                if left is None or right is None:
                    return None
                return False
            return _evaluate_comparison(
                current.operator,
                evaluate(current.left),
                evaluate(current.right),
            )
        raise ExpressionEvaluationError(
            f"Unsupported expression node {type(current).__name__}"
        )

    result = evaluate(node)
    if result is None or isinstance(result, bool):
        return result
    raise ExpressionEvaluationError(
        "Control expressions must evaluate to boolean or unknown, "
        f"got {type(result).__name__}"
    )
