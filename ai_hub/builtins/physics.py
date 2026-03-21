from typing import Any, Dict, List

from .registry import BuiltinSpec, register


_PHYS_CONSTANTS: Dict[str, float] = {
    "g": 9.81,
    "c": 299_792_458,
    "R": 8.314462618,
}


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "ohms_law",
            "description": "Tính V/I/R theo định luật Ohm (V = I*R). Cung cấp bất kỳ 2 giá trị.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "V": {"type": "number"},
                    "I": {"type": "number"},
                    "R": {"type": "number"},
                },
            },
        },
        {
            "name": "kinematics_v",
            "description": "Tính v = u + a*t.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "u": {"type": "number"},
                    "a": {"type": "number"},
                    "t": {"type": "number"},
                },
                "required": ["u", "a", "t"],
            },
        },
        {
            "name": "constants",
            "description": "Tra cứu hằng số vật lý: gia tốc trọng trường g=9.81 m/s², tốc độ ánh sáng c=3×10⁸ m/s, hằng số khí R=8.314 J/mol·K. Dùng khi hỏi về g, c, R trong bài toán vật lý, cơ học, nhiệt động lực học. Ví dụ: g bằng bao nhiêu, tốc độ ánh sáng là gì, hằng số khí R.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def resources() -> List[Dict[str, Any]]:
    return [
        {
            "uri": "physics://constants",
            "name": "Hằng số vật lý",
            "description": "Một số hằng số (g, c, R).",
            "mimeType": "application/json",
        },
        {
            "uri": "physics://formula_sheet/basic",
            "name": "Bảng công thức cơ bản",
            "description": "Một số công thức thường dùng (demo).",
            "mimeType": "text/plain",
        },
    ]


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}

    if tool_name == "ohms_law":
        V = args.get("V")
        I = args.get("I")
        R = args.get("R")
        provided = [x is not None for x in (V, I, R)].count(True)
        if provided < 2:
            raise ValueError("Provide at least two of V, I, R")
        if V is None:
            return {"V": I * R, "I": I, "R": R}
        if I is None:
            return {"V": V, "I": V / R, "R": R}
        return {"V": V, "I": I, "R": V / I}

    if tool_name == "kinematics_v":
        u = args.get("u")
        a = args.get("a")
        t = args.get("t")
        if u is None or a is None or t is None:
            raise ValueError("u, a, t are required")
        return {"v": u + a * t}

    if tool_name == "constants":
        return _PHYS_CONSTANTS

    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="physics",
        label="MCP tích hợp: Vật lý (demo)",
        name="physics-mcp (builtin)",
        version="0.1",
        description="MCP tích hợp cho các tiện ích vật lý cơ bản (demo).",
        tools=tools,
        resources=resources,
        call=call,
    )
)

