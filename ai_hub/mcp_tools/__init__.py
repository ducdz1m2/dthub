"""
MCP Tools Package - Các công cụ MCP được tổ chức theo chức năng
"""

from .device_tools import register_device_tools
from .dictionary_tools import register_dictionary_tools
from .knowledge_tools import register_knowledge_tools
from .science_tools import register_science_tools
from .system_tools import register_system_tools

__all__ = [
    'register_device_tools',
    'register_dictionary_tools',
    'register_knowledge_tools',
    'register_science_tools',
    'register_system_tools',
]
