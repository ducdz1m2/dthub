import re
from typing import Any, Dict, List, Tuple

from .registry import BuiltinSpec, register


_ATOMIC_WEIGHTS: Dict[str, float] = {
    "H": 1.008,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "Na": 22.990,
    "Cl": 35.45,
    "S": 32.06,
    "K": 39.0983,
    "Ca": 40.078,
    "Fe": 55.845,
}

_ELEMENTS: Dict[str, Dict[str, Any]] = {
    "H": {"name": "Hydrogen", "atomic_number": 1},
    "C": {"name": "Carbon", "atomic_number": 6},
    "N": {"name": "Nitrogen", "atomic_number": 7},
    "O": {"name": "Oxygen", "atomic_number": 8},
    "Na": {"name": "Sodium", "atomic_number": 11},
    "Cl": {"name": "Chlorine", "atomic_number": 17},
    "S": {"name": "Sulfur", "atomic_number": 16},
    "K": {"name": "Potassium", "atomic_number": 19},
    "Ca": {"name": "Calcium", "atomic_number": 20},
    "Fe": {"name": "Iron", "atomic_number": 26},
}


def _parse_formula(formula: str) -> Dict[str, int]:
    if not formula or not isinstance(formula, str):
        raise ValueError("formula is required")
    formula = formula.strip()
    if not formula:
        raise ValueError("formula is required")

    tokens: List[Tuple[str, str]] = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    if not tokens:
        raise ValueError("invalid formula")

    composition: Dict[str, int] = {}
    for symbol, count_str in tokens:
        if symbol not in _ATOMIC_WEIGHTS:
            raise ValueError(f"unsupported element: {symbol}")
        count = int(count_str) if count_str else 1
        composition[symbol] = composition.get(symbol, 0) + count

    return composition


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "lookup_element",
            "description": "Tra cứu thông tin cơ bản của nguyên tố theo ký hiệu (H, O, Na...).",
            "inputSchema": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
                "required": ["symbol"],
            },
        },
        {
            "name": "molar_mass",
            "description": "Tính khối lượng mol cho công thức đơn giản (không hỗ trợ ngoặc).",
            "inputSchema": {
                "type": "object",
                "properties": {"formula": {"type": "string"}},
                "required": ["formula"],
            },
        },
        {
            "name": "balance_equation",
            "description": "Cân bằng phương trình hóa học (bản demo).",
            "inputSchema": {
                "type": "object",
                "properties": {"equation": {"type": "string"}},
                "required": ["equation"],
            },
        },
    ]


def resources() -> List[Dict[str, Any]]:
    return [
        {
            "uri": "chem://constants/atomic_weights",
            "name": "Khối lượng nguyên tử (một phần)",
            "description": "Tập khối lượng nguyên tử dùng cho tool molar_mass.",
            "mimeType": "application/json",
        },
        {
            "uri": "chem://notes/balancing",
            "name": "Ghi chú cân bằng",
            "description": "Gợi ý nhanh về cân bằng phương trình (demo).",
            "mimeType": "text/plain",
        },
    ]


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}

    if tool_name == "lookup_element":
        symbol = (args.get("symbol") or "").strip()
        if not symbol:
            raise ValueError("symbol is required")
        element = _ELEMENTS.get(symbol)
        if not element:
            raise ValueError(f"unsupported element: {symbol}")
        return {
            "symbol": symbol,
            "name": element["name"],
            "atomic_number": element["atomic_number"],
            "atomic_weight": _ATOMIC_WEIGHTS.get(symbol),
        }

    if tool_name == "molar_mass":
        formula = (args.get("formula") or "").strip()
        composition = _parse_formula(formula)
        mass = 0.0
        for symbol, count in composition.items():
            mass += _ATOMIC_WEIGHTS[symbol] * count
        return {"formula": formula, "molar_mass": round(mass, 4), "composition": composition}

    if tool_name == "balance_equation":
        equation = (args.get("equation") or "").strip()
        if not equation:
            raise ValueError("equation is required")
        return {"input": equation, "balanced": equation, "note": "demo stub"}

    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="chemistry",
        label="MCP tích hợp: Hóa học (demo)",
        name="chemistry-mcp (builtin)",
        version="0.1",
        description="MCP tích hợp cho các tiện ích hóa học cơ bản (demo).",
        tools=tools,
        resources=resources,
        call=call,
    )
)

