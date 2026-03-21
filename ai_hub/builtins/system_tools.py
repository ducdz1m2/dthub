"""system_tools.py — đã gộp time_now vào system_info Django builtin, file này không còn tool nào."""
from .registry import BuiltinSpec, register


def tools():
    return []


def resources():
    return []


def call(tool_name, arguments):
    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="system",
        label="MCP tích hợp: Hệ thống",
        name="system-mcp (builtin)",
        version="0.2",
        description="(Trống — các tool hệ thống đã gộp vào Django API tools)",
        tools=tools,
        resources=resources,
        call=call,
    )
)
