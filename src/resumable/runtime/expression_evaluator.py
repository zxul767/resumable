import operator
from typing import Callable, cast

from ..frontend.ast_expressions import Binary, BinaryOp, Call, Expression, Literal, Neg, Var
from .core import CallableValue, Env, RuntimeContext, Value

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
        result = -value
        context.writer.debugln(f"[-({expr.expr}) => {result}]")
        return result

    if isinstance(expr, Binary):
        left_value = eval_expr(expr.left, env, context)
        right_value = eval_expr(expr.right, env, context)
        result = _binary_ops[expr.op](left_value, right_value)
        context.writer.debugln(
            f"[({expr.left}) {expr.op} ({expr.right}) => {result}]"
        )
        return result

    raise TypeError(f"Unsupported expression type: {type(expr).__name__}")
