import ast
import math
from typing import Any, Dict, List

from .registry import BuiltinSpec, register


_ALLOWED_FUNCS = {
    "abs": abs, "round": round,
    "ceil": math.ceil, "floor": math.floor,
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "log": math.log, "log10": math.log10, "exp": math.exp, "pow": pow,
}
_ALLOWED_CONSTS = {"pi": math.pi, "e": math.e}


def _eval_expr(expr: str) -> float:
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/")
    node = ast.parse(expr, mode="eval")

    def visit(n):
        if isinstance(n, ast.Expression): return visit(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return float(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = visit(n.operand); return v if isinstance(n.op, ast.UAdd) else -v
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)):
            l, r = visit(n.left), visit(n.right)
            ops = {ast.Add: l+r, ast.Sub: l-r, ast.Mult: l*r, ast.Div: l/r,
                   ast.FloorDiv: l//r, ast.Mod: l%r, ast.Pow: l**r}
            return ops[type(n.op)]
        if isinstance(n, ast.Name):
            if n.id in _ALLOWED_CONSTS: return float(_ALLOWED_CONSTS[n.id])
            raise ValueError(f"unknown identifier: {n.id}")
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            fn = _ALLOWED_FUNCS.get(n.func.id)
            if not fn: raise ValueError(f"function not allowed: {n.func.id}")
            return float(fn(*[visit(a) for a in n.args]))
        raise ValueError("unsupported syntax")

    return visit(node)


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "calc",
            "description": (
                "Tính biểu thức toán học. Hỗ trợ +−×÷**, sqrt/sin/cos/log/exp, pi, e. "
                "Ví dụ: sqrt(144) + 5^2, sin(pi/6), log(100)"
            ),
            "keywords": [
                "tính", "calculate", "calc", "bằng bao nhiêu", "kết quả",
                "sqrt", "sin", "cos", "log", "exp", "pow", "pi",
                "cộng", "trừ", "nhân", "chia", "lũy thừa", "căn bậc",
            ],
            "inputSchema": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
        {
            "name": "quadratic",
            "description": "Giải phương trình bậc 2: ax² + bx + c = 0.",
            "keywords": [
                "phương trình bậc 2", "phương trình bậc hai", "quadratic",
                "nghiệm", "delta", "discriminant", "ax2", "ax^2",
            ],
            "inputSchema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"}, "b": {"type": "number"}, "c": {"type": "number"}
                },
                "required": ["a", "b", "c"],
            },
        },
    ]


def resources() -> List[Dict[str, Any]]:
    return []


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}

    if tool_name == "calc":
        expr = (args.get("expression") or "").strip()
        if not expr:
            raise ValueError("expression is required")
        value = _eval_expr(expr)
        return {"expression": expr, "value": value}

    if tool_name == "quadratic":
        a, b, c = args.get("a"), args.get("b"), args.get("c")
        if a is None or b is None or c is None:
            raise ValueError("a, b, c are required")
        a, b, c = float(a), float(b), float(c)
        if a == 0:
            if b == 0: raise ValueError("invalid equation")
            return {"type": "linear", "roots": [-c / b]}
        d = b*b - 4*a*c
        if d < 0: return {"type": "quadratic", "discriminant": d, "roots": []}
        sq = math.sqrt(d)
        roots = [(-b + sq) / (2*a)] if d == 0 else [(-b + sq) / (2*a), (-b - sq) / (2*a)]
        return {"type": "quadratic", "discriminant": d, "roots": roots}

    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="math",
        label="MCP tích hợp: Toán (calc, phương trình bậc 2)",
        name="math-mcp (builtin)",
        version="0.2",
        description="Tính toán và giải phương trình bậc 2.",
        tools=tools,
        resources=resources,
        call=call,
    )
)
