"""
Property-based tests và unit tests cho ToolOrchestrator.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 7.2**
"""
from __future__ import annotations

import asyncio
import pytest
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

# Import module under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ai_hub.mcp_tools.tool_orchestrator import ToolOrchestrator, ToolResult


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

@dataclass
class MockRouterDecision:
    tools: list


def make_decision(tool_names: list[str]) -> MockRouterDecision:
    return MockRouterDecision(tools=[{"name": n, "parameters": {}} for n in tool_names])


def make_orchestrator(
    check_access_fn=None,
    dispatcher_tools: dict | None = None,
    tool_timeout: float = 10.0,
) -> ToolOrchestrator:
    """Tạo ToolOrchestrator với mock dependencies."""
    dispatcher = MagicMock()
    dispatcher.tools = dispatcher_tools or {}

    retriever = MagicMock()

    if check_access_fn is None:
        async def _allow_all(user_id, tool_name):
            return True, None
        check_access_fn = _allow_all

    return ToolOrchestrator(
        dispatcher=dispatcher,
        retriever=retriever,
        check_access_fn=check_access_fn,
        tool_timeout=tool_timeout,
    )


# ---------------------------------------------------------------------------
# Property 4: Tool Orchestrator completeness — N tools in, N results out
# **Validates: Requirements 3.1, 3.4**
# ---------------------------------------------------------------------------

@given(
    tool_names=st.lists(
        st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"), min_size=1, max_size=20),
        min_size=0,
        max_size=10,
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_orchestrator_completeness_n_tools_n_results(tool_names):
    """
    Property 4: Tool Orchestrator completeness — N tools in, N results out.

    **Validates: Requirements 3.1, 3.4**
    """
    decision = make_decision(tool_names)

    async def _allow_all(user_id, tool_name):
        return True, None

    async def fake_execute_single(tool_name, params, query, user_id):
        return ToolResult(tool_name=tool_name, result="ok", success=True, error=None, execution_time_ms=1.0)

    orchestrator = make_orchestrator(check_access_fn=_allow_all)

    async def run():
        with patch.object(orchestrator, "_execute_single", side_effect=fake_execute_single):
            return await orchestrator.execute(decision, "test query", user_id=1)

    results = asyncio.get_event_loop().run_until_complete(run())
    assert len(results) == len(tool_names)


# ---------------------------------------------------------------------------
# Property 5: Tool Orchestrator fault tolerance
# **Validates: Requirements 3.2, 3.3**
# ---------------------------------------------------------------------------

@given(
    tool_names=st.lists(
        st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"), min_size=1, max_size=20),
        min_size=1,
        max_size=8,
    ),
    fail_indices=st.frozensets(st.integers(min_value=0, max_value=7)),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_orchestrator_fault_tolerance(tool_names, fail_indices):
    """
    Property 5: Tool Orchestrator fault tolerance.

    Khi một số tool raise exception, execute() vẫn trả về đủ N kết quả.
    Tool lỗi có success=False, tool thành công có success=True.

    **Validates: Requirements 3.2, 3.3**
    """
    decision = make_decision(tool_names)
    # Chỉ fail các index thực sự tồn tại trong danh sách
    actual_fail = {i for i in fail_indices if i < len(tool_names)}

    async def _allow_all(user_id, tool_name):
        return True, None

    call_count = [0]

    async def fake_execute_single(tool_name, params, query, user_id):
        idx = call_count[0]
        call_count[0] += 1
        if idx in actual_fail:
            raise RuntimeError(f"Simulated failure for {tool_name}")
        return ToolResult(tool_name=tool_name, result="ok", success=True, error=None, execution_time_ms=1.0)

    orchestrator = make_orchestrator(check_access_fn=_allow_all)

    async def run():
        with patch.object(orchestrator, "_execute_single", side_effect=fake_execute_single):
            return await orchestrator.execute(decision, "test query", user_id=1)

    results = asyncio.get_event_loop().run_until_complete(run())

    # Phải có đúng N kết quả
    assert len(results) == len(tool_names)

    # Kiểm tra success/failure theo index
    for i, r in enumerate(results):
        assert isinstance(r.success, bool)
        if i in actual_fail:
            assert r.success is False
        else:
            assert r.success is True


# ---------------------------------------------------------------------------
# Property 6: Permission enforcement trước khi thực thi
# **Validates: Requirements 3.5**
# ---------------------------------------------------------------------------

@given(
    tool_names=st.lists(
        st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"), min_size=1, max_size=20),
        min_size=1,
        max_size=8,
    ),
    denied_indices=st.frozensets(st.integers(min_value=0, max_value=7)),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_orchestrator_permission_enforcement(tool_names, denied_indices):
    """
    Property 6: Tool Orchestrator kiểm tra permission trước khi thực thi.

    Tool bị denied không được gọi handler, trả về ToolResult(success=False).

    **Validates: Requirements 3.5**
    """
    decision = make_decision(tool_names)
    actual_denied = {tool_names[i] for i in denied_indices if i < len(tool_names)}

    handler_called_for = []

    async def check_access(user_id, tool_name):
        if tool_name in actual_denied:
            return False, f"403: Không có quyền truy cập tool '{tool_name}'"
        return True, None

    async def fake_call_tool(tool_name, params, query):
        handler_called_for.append(tool_name)
        return "result"

    orchestrator = make_orchestrator(check_access_fn=check_access)

    async def run():
        with patch.object(orchestrator, "_call_tool", side_effect=fake_call_tool):
            return await orchestrator.execute(decision, "test query", user_id=1)

    results = asyncio.get_event_loop().run_until_complete(run())

    # Các tool bị denied không được gọi handler
    for name in actual_denied:
        assert name not in handler_called_for

    # Các tool bị denied phải có success=False
    for r in results:
        if r.tool_name in actual_denied:
            assert r.success is False
            assert r.error is not None
            assert "403" in r.error


# ---------------------------------------------------------------------------
# Property 8: ToolResult luôn có đủ trường observability
# **Validates: Requirements 7.2**
# ---------------------------------------------------------------------------

@given(
    tool_name=st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"), min_size=1, max_size=30),
    params=st.dictionaries(
        st.text(min_size=1, max_size=10),
        st.text(min_size=0, max_size=50),
        max_size=5,
    ),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_tool_result_observability_fields(tool_name, params):
    """
    Property 8: ToolResult luôn có đủ trường cần thiết cho observability.

    tool_name khớp với tool được yêu cầu, execution_time_ms >= 0, success là boolean.

    **Validates: Requirements 7.2**
    """
    async def _allow_all(user_id, tn):
        return True, None

    async def fake_call_tool(tn, p, q):
        return "result"

    orchestrator = make_orchestrator(check_access_fn=_allow_all)
    decision = MockRouterDecision(tools=[{"name": tool_name, "parameters": params}])

    async def run():
        with patch.object(orchestrator, "_call_tool", side_effect=fake_call_tool):
            return await orchestrator.execute(decision, "query", user_id=1)

    results = asyncio.get_event_loop().run_until_complete(run())
    assert len(results) == 1
    r = results[0]

    # tool_name phải khớp
    assert r.tool_name == tool_name
    # execution_time_ms >= 0
    assert r.execution_time_ms >= 0.0
    # success là boolean
    assert isinstance(r.success, bool)


# ---------------------------------------------------------------------------
# Unit Tests (Task 4.5)
# ---------------------------------------------------------------------------

def test_empty_decision_returns_empty_list():
    """Test empty decision: RouterDecision(tools=[]) → trả về []."""
    orchestrator = make_orchestrator()
    decision = make_decision([])

    async def run():
        return await orchestrator.execute(decision, "query", user_id=1)

    results = asyncio.get_event_loop().run_until_complete(run())
    assert results == []


def test_tool_timeout_returns_failure():
    """Test timeout per-tool: mock handler sleep 15s → ToolResult(success=False, error contains 'timeout')."""
    async def _allow_all(user_id, tool_name):
        return True, None

    async def slow_tool(tool_name, params, query):
        await asyncio.sleep(15)
        return "should not reach"

    orchestrator = make_orchestrator(check_access_fn=_allow_all, tool_timeout=0.05)
    decision = make_decision(["slow_tool"])

    async def run():
        with patch.object(orchestrator, "_call_tool", side_effect=slow_tool):
            return await orchestrator.execute(decision, "query", user_id=1)

    results = asyncio.get_event_loop().run_until_complete(run())
    assert len(results) == 1
    r = results[0]
    assert r.success is False
    assert "timeout" in r.error
    assert r.execution_time_ms >= 0.0


def test_all_tools_fail_returns_n_failure_results():
    """Test all tools fail: tất cả tool raise exception → vẫn trả về N results với success=False."""
    async def _allow_all(user_id, tool_name):
        return True, None

    async def failing_tool(tool_name, params, query):
        raise ValueError(f"Simulated error for {tool_name}")

    orchestrator = make_orchestrator(check_access_fn=_allow_all)
    tool_names = ["tool_a", "tool_b", "tool_c"]
    decision = make_decision(tool_names)

    async def run():
        with patch.object(orchestrator, "_call_tool", side_effect=failing_tool):
            return await orchestrator.execute(decision, "query", user_id=1)

    results = asyncio.get_event_loop().run_until_complete(run())
    assert len(results) == 3
    for r in results:
        assert r.success is False
        assert r.error is not None


def test_permission_denied_does_not_call_handler():
    """Test permission denied: handler không được gọi, ToolResult(success=False) được trả về."""
    handler_called = []

    async def deny_all(user_id, tool_name):
        return False, f"403: Không có quyền truy cập tool '{tool_name}'"

    async def fake_call_tool(tool_name, params, query):
        handler_called.append(tool_name)
        return "result"

    orchestrator = make_orchestrator(check_access_fn=deny_all)
    decision = make_decision(["secret_tool"])

    async def run():
        with patch.object(orchestrator, "_call_tool", side_effect=fake_call_tool):
            return await orchestrator.execute(decision, "query", user_id=1)

    results = asyncio.get_event_loop().run_until_complete(run())
    assert len(results) == 1
    assert results[0].success is False
    assert "403" in results[0].error
    assert "secret_tool" not in handler_called


def test_successful_tool_execution():
    """Test tool thực thi thành công trả về ToolResult(success=True)."""
    async def _allow_all(user_id, tool_name):
        return True, None

    async def good_tool(tool_name, params, query):
        return {"data": "some result"}

    orchestrator = make_orchestrator(check_access_fn=_allow_all)
    decision = make_decision(["good_tool"])

    async def run():
        with patch.object(orchestrator, "_call_tool", side_effect=good_tool):
            return await orchestrator.execute(decision, "query", user_id=1)

    results = asyncio.get_event_loop().run_until_complete(run())
    assert len(results) == 1
    r = results[0]
    assert r.success is True
    assert r.error is None
    assert r.result == {"data": "some result"}
    assert r.execution_time_ms >= 0.0
