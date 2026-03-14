"""
MCP Client for DTHub AI Hub
Communicates with ESP8266 MCP Servers via HTTP and MQTT
"""

import json
import requests
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from .models import MCPServer as MCPServerModel
from .utils.ngrok_manager import ngrok_manager
import logging

logger = logging.getLogger(__name__)

class MCPServer:
    """Represents an MCP Server (ESP8266 device)"""
    
    def __init__(self, device_id: str, endpoint: str, auth_token: str = None):
        self.device_id = device_id
        self.endpoint = endpoint  # Dynamic endpoint instead of static IP
        self.auth_token = auth_token
        self.capabilities = {}
        self.resources = []
        self.tools = []
        self.is_online = False
        self.last_seen = None
        self.last_error: Optional[str] = None
        
    def get_info(self) -> Dict[str, Any]:
        """Get device info via HTTP"""
        try:
            self.last_error = None
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            response = requests.get(f"{self.endpoint}/info", headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
            self.last_error = f"HTTP {response.status_code} from /info"
        except Exception as e:
            logger.error(f"Failed to get info from {self.device_id}: {e}")
            self.last_error = str(e)
        return {}
    
    def get_mcp_info(self) -> Dict[str, Any]:
        """Get MCP server capabilities"""
        try:
            self.last_error = None
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            response = requests.get(f"{self.endpoint}/mcp/info", headers=headers, timeout=5)
            if response.status_code == 200:
                try:
                    self.capabilities = response.json() or {}
                except Exception:
                    self.capabilities = {}
                self.is_online = True
                self.last_seen = datetime.now()
                return self.capabilities
            self.last_error = f"HTTP {response.status_code} from /mcp/info"
        except Exception as e:
            logger.error(f"Failed to get MCP info from {self.device_id}: {e}")
            self.last_error = str(e)
        self.is_online = False
        return {}
    
    def get_resources(self) -> List[Dict[str, Any]]:
        """Get available resources"""
        try:
            self.last_error = None
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            response = requests.get(f"{self.endpoint}/mcp/resources", headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.resources = data.get('resources', [])
                return self.resources
            self.last_error = f"HTTP {response.status_code} from /mcp/resources"
        except Exception as e:
            logger.error(f"Failed to get resources from {self.device_id}: {e}")
            self.last_error = str(e)
        return []
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools"""
        try:
            self.last_error = None
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            response = requests.get(f"{self.endpoint}/mcp/tools", headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.tools = data.get('tools', [])
                return self.tools
            self.last_error = f"HTTP {response.status_code} from /mcp/tools"
        except Exception as e:
            logger.error(f"Failed to get tools from {self.device_id}: {e}")
            self.last_error = str(e)
        return []
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        try:
            self.last_error = None
            headers = {'Content-Type': 'application/json'}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            payload = {
                "name": tool_name,
                "arguments": arguments
            }
            response = requests.post(
                f"{self.endpoint}/mcp/call",
                json=payload,
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            self.last_error = f"HTTP {response.status_code} from /mcp/call"
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on {self.device_id}: {e}")
            self.last_error = str(e)
            return {"error": str(e)}
        return {"error": f"Tool call failed: {tool_name}"}

class MCPClient:
    """MCP Client for managing multiple ESP8266 MCP servers"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.discovery_lock = threading.Lock()
        
    
    def register_server(self, device_id: str, local_ip: str, local_port: int = 80, auth_token: str = None) -> bool:
        """Register a new MCP server with ngrok tunnel"""
        # Create ngrok tunnel
        public_url = ngrok_manager.create_tunnel(device_id, local_port, local_ip)
        
        if public_url:
            server = MCPServer(device_id, public_url, auth_token)
            
            # REAL MODE: Test connection and get capabilities
            capabilities = server.get_mcp_info()
            if server.is_online:
                self.servers[device_id] = server
                logger.info(f"Registered MCP server: {device_id} at {public_url}")
                return True
            else:
                # If connection fails, close tunnel
                ngrok_manager.close_tunnel(device_id)
                logger.error(f"Failed to register MCP server: {device_id} - connection failed")
        else:
            logger.error(f"Failed to register MCP server: {device_id} - tunnel creation failed")
            
        return False

    def register_server_endpoint(self, device_id: str, endpoint: str, auth_token: str = None, test_connection: bool = True) -> bool:
        endpoint = (endpoint or "").strip().rstrip("/")
        if not endpoint:
            return False

        server = MCPServer(device_id, endpoint, auth_token)
        self.servers[device_id] = server

        if not test_connection:
            return True

        server.get_mcp_info()
        if server.is_online:
            server.get_resources()
            server.get_tools()
            return True
        return False
    
    def unregister_server(self, device_id: str):
        """Unregister an MCP server"""
        if device_id in self.servers:
            del self.servers[device_id]
            # Close ngrok tunnel
            ngrok_manager.close_tunnel(device_id)
            logger.info(f"Unregistered MCP server: {device_id}")
    
    def get_server(self, device_id: str) -> Optional[MCPServer]:
        """Get a specific MCP server"""
        return self.servers.get(device_id)
    
    def get_all_servers(self) -> List[MCPServer]:
        """Get all registered MCP servers"""
        return list(self.servers.values())
    
    def get_online_servers(self) -> List[MCPServer]:
        """Get all online MCP servers"""
        return [s for s in self.servers.values() if s.is_online]

    def discover_servers(self) -> List[str]:
        """Discover MCP servers from MCPServer database - Optimized"""
        discovered = []
        
        with self.discovery_lock:
            try:
                servers = MCPServerModel.objects.filter(is_active=True).only(
                    'device_id',
                    'auth_token',
                    'domain',
                    'subdomain',
                    'connection_method',
                )
                
                for server in servers:
                    if server.device_id not in self.servers:
                        endpoint = server.get_endpoint
                        if endpoint:
                            self.register_server_endpoint(server.device_id, endpoint, server.auth_token, test_connection=True)
                            discovered.append(server.device_id)
            except Exception as e:
                logger.error(f"Error in discover_servers: {e}")
        
        return discovered
    
    def refresh_server_capabilities(self, device_id: str) -> bool:
        """Refresh capabilities of a specific server"""
        if device_id in self.servers:
            server = self.servers[device_id]
            server.get_mcp_info()
            if server.is_online:
                server.get_resources()
                server.get_tools()
                return True
        return False
    
    def call_tool(self, device_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on a specific MCP server"""
        if device_id in self.servers:
            server = self.servers[device_id]
            return server.call_tool(tool_name, arguments)
        return {"error": f"Server {device_id} not found"}
    
    
    def get_all_resources(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all resources from all servers"""
        resources = {}
        for device_id, server in self.servers.items():
            if server.is_online:
                resources[device_id] = server.resources
        return resources
    
    def get_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all tools from all servers"""
        tools = {}
        for device_id, server in self.servers.items():
            if server.is_online:
                tools[device_id] = server.tools
        return tools
    
    def health_check(self) -> Dict[str, bool]:
        """Perform health check on all servers"""
        health_status = {}
        
        for device_id, server in self.servers.items():
            try:
                info = server.get_info()
                if info:
                    server.is_online = True
                    server.last_seen = datetime.now()
                    health_status[device_id] = True
                else:
                    server.is_online = False
                    health_status[device_id] = False
            except Exception as e:
                server.is_online = False
                health_status[device_id] = False
                logger.error(f"Health check failed for {device_id}: {e}")
        
        return health_status


class MCPDiscoveryClient:
    """
    Client chuyên dụng để quét và đồng bộ hóa công cụ từ MCP Servers (FastAPI)
    Dùng cho kiến trúc Agentic MCP mới.
    """
    
    @staticmethod
    def discover_tools(server_id: int) -> Dict[str, Any]:
        """
        Quét URL của server và cập nhật danh sách MCPTool trong Database
        """
        from .models import MCPServer, MCPTool
        
        try:
            server = MCPServer.objects.get(pk=server_id)
            endpoint = server.get_endpoint
            if not endpoint:
                return {"status": "error", "message": "Server không có endpoint hợp lệ"}
            
            headers = {}
            if server.auth_token:
                # Dùng X-Token cho FastAPI template hoặc Authorization cho ESP8266
                headers['X-Token'] = server.auth_token
                headers['Authorization'] = f'Bearer {server.auth_token}'
                
            # Thử gọi /metadata (chuẩn mới) hoặc /mcp/tools (chuẩn cũ ESP8266)
            response = None
            try:
                response = requests.get(f"{endpoint}/metadata", headers=headers, timeout=10)
                if response.status_code != 200:
                    response = requests.get(f"{endpoint}/mcp/tools", headers=headers, timeout=10)
            except Exception as e:
                return {"status": "error", "message": f"Không thể kết nối đến server: {str(e)}"}

            if response.status_code != 200:
                return {"status": "error", "message": f"Server trả về lỗi {response.status_code}"}
            
            data = response.json()
            tools_data = data.get('tools', [])
            
            # Cập nhật database
            synced_count = 0
            for tool_info in tools_data:
                # Tool info format: {name, display_name, description, parameters/schema}
                tool_id = tool_info.get('name')
                if not tool_id: continue
                
                # Tạo hoặc cập nhật MCPTool
                tool, created = MCPTool.objects.update_or_create(
                    name=f"{server.device_id}_{tool_id}", # Unique name
                    defaults={
                        'display_name': tool_info.get('display_name', tool_id),
                        'description': tool_info.get('description', ''),
                        'tool_type': 'external_api',
                        'server': server,
                        'api_endpoint': f"{endpoint}/execute",
                        'api_method': 'POST',
                        'mcp_schema': tool_info.get('parameters', tool_info.get('schema', {})),
                        'is_enabled': True,
                        'category': data.get('server_name', 'External MCP')
                    }
                )
                synced_count += 1
                
            return {
                "status": "success", 
                "message": f"Đã đồng bộ {synced_count} công cụ từ {server.name}",
                "tools_count": synced_count
            }
            
        except MCPServer.DoesNotExist:
            return {"status": "error", "message": "Server không tồn tại"}
        except Exception as e:
            logger.error(f"Lỗi trong discover_tools: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def execute_remote_tool(tool_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thực thi một tool từ xa thông qua MCP Server
        """
        from .models import MCPTool
        
        try:
            tool = MCPTool.objects.get(name=tool_id)
            if not tool.server or not tool.api_endpoint:
                return {"status": "error", "message": "Tool không có server hoặc endpoint cấu hình"}
            
            headers = {
                'Content-Type': 'application/json'
            }
            if tool.server.auth_token:
                headers['X-Token'] = tool.server.auth_token
                headers['Authorization'] = f'Bearer {tool.server.auth_token}'
                
            payload = {
                "tool": tool.name.replace(f"{tool.server.device_id}_", ""), # Gửi tên gốc cho server
                "parameters": arguments
            }
            
            response = requests.post(
                tool.api_endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "error", 
                    "message": f"Server trả về lỗi {response.status_code}: {response.text}"
                }
                
        except MCPTool.DoesNotExist:
            return {"status": "error", "message": f"Tool {tool_id} không tồn tại trong hệ thống"}
        except Exception as e:
            logger.error(f"Lỗi khi thực thi tool {tool_id}: {e}")
            return {"status": "error", "message": str(e)}

# Global MCP client instance
mcp_client = MCPClient()

def initialize_mcp_client():
    """Initialize the MCP client"""
    mcp_client.discover_servers()
    logger.info("MCP Client initialized")

def get_mcp_client() -> MCPClient:
    """Get the global MCP client instance"""
    return mcp_client
