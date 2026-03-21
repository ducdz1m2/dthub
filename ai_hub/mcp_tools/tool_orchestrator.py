"""
Tool Orchestrator — thực thi MCP tools song song và thu thập kết quả.
"""
from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

@dataclass
class ToolResult:
    tool_name: str
    result: Any
    success: bool
    error: str | None
    execution_time_ms: float

class ToolOrchestrator:
    def __init__(self, dispatcher, check_access_fn: Callable, tool_timeout: float = 10.0):
        self.dispatcher = dispatcher
        self.check_access_fn = check_access_fn  # async (user_id, tool_name) -> (bool, str)
        self.tool_timeout = tool_timeout

    async def execute(self, decision, query: str, user_id) -> list[ToolResult]:
        """Thực thi tất cả tools trong RouterDecision song song."""
        if not decision.tools:
            return []
        
        coroutines = [
            self._execute_single(t["name"], t.get("parameters", {}), query, user_id)
            for t in decision.tools
        ]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Convert exceptions thành ToolResult lỗi
        final = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                tool_name = decision.tools[i]["name"]
                final.append(ToolResult(tool_name=tool_name, result=None, success=False, error=str(r), execution_time_ms=0.0))
            else:
                final.append(r)
        return final

    async def _execute_single(self, tool_name: str, params: dict, query: str, user_id) -> ToolResult:
        """Thực thi một tool đơn lẻ với permission check và timeout."""
        start = time.monotonic()
        
        # 1. Permission check
        has_access, error_msg = await self.check_access_fn(user_id, tool_name)
        if not has_access:
            return ToolResult(tool_name=tool_name, result=None, success=False, error=error_msg, execution_time_ms=0.0)
        
        # 2. Thực thi với timeout
        try:
            # Inject user_id vào params để handler có thể dùng
            params_with_uid = dict(params) if params else {}
            if user_id and "user_id" not in params_with_uid:
                params_with_uid["user_id"] = user_id

            result = await asyncio.wait_for(
                self._call_tool(tool_name, params_with_uid, query),
                timeout=self.tool_timeout
            )
            elapsed = (time.monotonic() - start) * 1000
            logger.info("[TOOL_ORCHESTRATOR] tool=%s success=True time_ms=%.1f", tool_name, elapsed)
            return ToolResult(tool_name=tool_name, result=result, success=True, error=None, execution_time_ms=elapsed)
        except asyncio.TimeoutError:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning("[TOOL_ORCHESTRATOR] tool=%s TIMEOUT after %.1fs", tool_name, self.tool_timeout)
            return ToolResult(tool_name=tool_name, result=None, success=False, error=f"timeout after {self.tool_timeout}s", execution_time_ms=elapsed)
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("[TOOL_ORCHESTRATOR] tool=%s error=%s", tool_name, e)
            return ToolResult(tool_name=tool_name, result=None, success=False, error=str(e), execution_time_ms=elapsed)

    async def _call_tool(self, tool_name: str, params: dict, query: str):
        """Gọi tool handler — external API hoặc built-in dispatcher."""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def find_tool_obj():
            from ai_hub.models import MCPTool
            try:
                return MCPTool.objects.get(name=tool_name)
            except MCPTool.DoesNotExist:
                return None
        
        tool_obj = await find_tool_obj()
        
        if tool_obj and tool_obj.tool_type == 'external_api':
            # External MCP Server
            from ai_hub.mcp_client import MCPDiscoveryClient
            return await sync_to_async(MCPDiscoveryClient.execute_remote_tool)(tool_name, params)
        
        # Built-in dispatcher
        if tool_name in self.dispatcher.tools:
            handler = self.dispatcher.tools[tool_name]["handler"]
            # Truyền query string — handler nhận string
            query_str = params.get("query", query) if params else query
            user_id_val = params.get("user_id") if params else None
            return await sync_to_async(handler)(query_str, user_id=user_id_val)
        
        raise ValueError(f"Handler không tìm thấy cho tool: {tool_name}")
