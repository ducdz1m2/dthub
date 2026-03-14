import ast
import math
from typing import Any, Dict, List

from .registry import BuiltinSpec, register


_ALLOWED_FUNCS = {
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pow": pow,
}

_ALLOWED_CONSTS = {"pi": math.pi, "e": math.e}


def _eval_expr(expr: str) -> float:
    node = ast.parse(expr, mode="eval")

    def visit(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return visit(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = visit(n.operand)
            return v if isinstance(n.op, ast.UAdd) else -v
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)):
            left = visit(n.left)
            right = visit(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            if isinstance(n.op, ast.Sub):
                return left - right
            if isinstance(n.op, ast.Mult):
                return left * right
            if isinstance(n.op, ast.Div):
                return left / right
            if isinstance(n.op, ast.FloorDiv):
                return left // right
            if isinstance(n.op, ast.Mod):
                return left % right
            return left**right
        if isinstance(n, ast.Name):
            if n.id in _ALLOWED_CONSTS:
                return float(_ALLOWED_CONSTS[n.id])
            raise ValueError(f"unknown identifier: {n.id}")
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            fn = _ALLOWED_FUNCS.get(n.func.id)
            if not fn:
                raise ValueError(f"function not allowed: {n.func.id}")
            args = [visit(a) for a in n.args]
            return float(fn(*args))
        raise ValueError("expression contains unsupported syntax")

    return visit(node)


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "calc",
            "description": "Tính biểu thức toán (an toàn, không dùng eval). Hỗ trợ + - * / **, pi, e và hàm như sqrt/sin/cos/log.",
            "inputSchema": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
        {
            "name": "quadratic",
            "description": "Giải phương trình bậc 2: ax^2 + bx + c = 0.",
            "inputSchema": {
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}, "c": {"type": "number"}},
                "required": ["a", "b", "c"],
            },
        },
        {
            "name": "stats_basic",
            "description": "Tính thống kê cơ bản (min/max/mean/median) cho danh sách số.",
            "inputSchema": {
                "type": "object",
                "properties": {"numbers": {"type": "array", "items": {"type": "number"}}},
                "required": ["numbers"],
            },
        },
    ]


def resources() -> List[Dict[str, Any]]:
    return [
        {
            "uri": "math://help/calc",
            "name": "Calc help",
            "description": "Các hàm hỗ trợ: abs, round, ceil, floor, sqrt, sin, cos, tan, log, log10, exp, pow; hằng số: pi, e.",
            "mimeType": "text/plain",
        }
    ]


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}

    if tool_name == "calc":
        expr = (args.get("expression") or "").strip()
        if not expr:
            raise ValueError("expression is required")
        value = _eval_expr(expr)
        return {"expression": expr, "value": value}

    if tool_name == "quadratic":
        a = args.get("a")
        b = args.get("b")
        c = args.get("c")
        if a is None or b is None or c is None:
            raise ValueError("a, b, c are required")
        a = float(a)
        b = float(b)
        c = float(c)
        if a == 0:
            if b == 0:
                raise ValueError("invalid equation")
            return {"type": "linear", "root": -c / b}
        d = b * b - 4 * a * c
        if d < 0:
            return {"type": "quadratic", "discriminant": d, "roots": []}
        sqrt_d = math.sqrt(d)
        x1 = (-b + sqrt_d) / (2 * a)
        x2 = (-b - sqrt_d) / (2 * a)
        roots = [x1] if d == 0 else [x1, x2]
        return {"type": "quadratic", "discriminant": d, "roots": roots}

    if tool_name == "stats_basic":
        numbers = args.get("numbers")
        if not isinstance(numbers, list) or not numbers:
            raise ValueError("numbers must be a non-empty array")
        vals = [float(x) for x in numbers]
        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        mid = n // 2
        median = vals_sorted[mid] if n % 2 == 1 else (vals_sorted[mid - 1] + vals_sorted[mid]) / 2
        mean = sum(vals_sorted) / n
        return {"count": n, "min": vals_sorted[0], "max": vals_sorted[-1], "mean": mean, "median": median}

    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="math",
        label="MCP tích hợp: Toán (calc, thống kê...)",
        name="math-mcp (builtin)",
        version="0.1",
        description="Các tiện ích toán học chạy trực tiếp trong DTHub.",
        tools=tools,
        resources=resources,
        call=call,
    )
)

