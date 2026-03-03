import operator
from typing import Callable, cast

from ..frontend.ast_expressions import Binary, BinaryOp, Call, Expression, Literal, Neg, Var
from .core import (
    CallableValue,
    Env,
    RuntimeContext,
    Value,
    format_repl_value,
    value_type_name,
)

_binary_ops: dict[BinaryOp, Callable[[Value, Value], Value]] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "==": operator.eq,
    "<=": operator.le,
    "<": operator.lt,
    "mod": operator.mod,
}


def _is_number(value: Value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def eval_expr(expr: Expression, env: Env, context: RuntimeContext) -> Value:
    if isinstance(expr, Literal):
        return expr.value

    if isinstance(expr, Var):
        return env[expr.name]

    if isinstance(expr, Call):
        callee = env[expr.callee_name]
        if not callable(callee):
            raise ValueError(f"{expr.callee_name} is not callable")
        callable_value = cast(CallableValue, callee)
        args = [eval_expr(arg, env, context) for arg in expr.args]
        return callable_value(args, context)

    if isinstance(expr, Neg):
        value = eval_expr(expr.expr, env, context)
        if not _is_number(value):
            raise ValueError(
                "invalid operand for unary '-': "
                f"{value_type_name(value)} ({format_repl_value(value)})"
            )
        result = -value
        context.writer.debugln(f"[-({expr.expr}) => {result}]")
        return result

    if isinstance(expr, Binary):
        left_value = eval_expr(expr.left, env, context)
        right_value = eval_expr(expr.right, env, context)
        if expr.op in {"+", "-", "*", "/", "mod", "<", "<="}:
            if not _is_number(left_value) or not _is_number(right_value):
                raise ValueError(
                    "invalid operands for "
                    f"'{expr.op}': {value_type_name(left_value)} ({format_repl_value(left_value)}) "
                    f"and {value_type_name(right_value)} ({format_repl_value(right_value)})"
                )
        try:
            result = _binary_ops[expr.op](left_value, right_value)
        except Exception as error:
            raise ValueError(
                "runtime error while evaluating "
                f"'{expr.op}' with {format_repl_value(left_value)} and {format_repl_value(right_value)}: "
                f"{error}"
            ) from error
        context.writer.debugln(
            f"[({expr.left}) {expr.op} ({expr.right}) => {result}]"
        )
        return result

    raise TypeError(f"Unsupported expression type: {type(expr).__name__}")
