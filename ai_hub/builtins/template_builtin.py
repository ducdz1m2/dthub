from typing import Any, Dict, List

from .registry import BuiltinSpec, register


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "hello",
            "description": "Ví dụ tool đơn giản.",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        }
    ]


def resources() -> List[Dict[str, Any]]:
    return [
        {
            "uri": "example://readme",
            "name": "Readme",
            "description": "Ví dụ resource.",
            "mimeType": "text/plain",
        }
    ]


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}
    if tool_name == "hello":
        name = (args.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")
        return {"message": f"Xin chào {name}"}
    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="example",
        label="MCP tích hợp: Example",
        name="example-mcp (builtin)",
        version="0.1",
        description="Ví dụ builtin MCP để bạn copy và sửa.",
        tools=tools,
        resources=resources,
        call=call,
    )
)

