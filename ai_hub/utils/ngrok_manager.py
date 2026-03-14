"""
Ngrok Tunnel Manager for MCP System
Quản lý ngrok tunnels cho ESP8266 devices
"""

import json
import subprocess
import requests
import time
from typing import Dict, Optional
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class NgrokManager:
    """Quản lý ngrok tunnels cho MCP devices"""
    
    def __init__(self):
        self.ngrok_path = "ngrok"  # Assume ngrok is in PATH
        self.active_tunnels: Dict[str, Dict] = {}
        
    def get_ngrok_tunnels(self) -> Dict:
        """Lấy danh sách tunnels đang chạy từ ngrok API"""
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get ngrok tunnels: {e}")
        return {"tunnels": []}
    
    def create_tunnel(self, device_id: str, local_port: int, local_ip: str = "localhost") -> Optional[str]:
        """Tạo ngrok tunnel cho device"""
        try:
            if getattr(settings, "MCP_MOCK_MODE", False):
                fake_url = f"https://{device_id}.ngrok.io"
                self.active_tunnels[device_id] = {
                    "public_url": fake_url,
                    "local_port": local_port,
                    "local_ip": local_ip,
                    "process": None
                }
                logger.info(f"Created MOCK ngrok tunnel for {device_id}: {fake_url}")
                return fake_url

            current = self.active_tunnels.get(device_id)
            if current and current.get("public_url"):
                if current.get("local_ip") == local_ip and current.get("local_port") == local_port:
                    return current.get("public_url")

            cmd = [
                self.ngrok_path,
                "http",
                f"{local_ip}:{local_port}",
                "--log=stdout",
                "--log-level=info"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            time.sleep(2)

            tunnels = self.get_ngrok_tunnels()
            desired_addr = f"{local_ip}:{local_port}"

            public_url = None
            for tunnel in tunnels.get("tunnels", []):
                config = tunnel.get("config") or {}
                if config.get("addr") == desired_addr and tunnel.get("public_url"):
                    public_url = tunnel.get("public_url")
                    break

            if not public_url:
                for tunnel in tunnels.get("tunnels", []):
                    if tunnel.get("public_url"):
                        public_url = tunnel.get("public_url")
                        break

            if public_url:
                self.active_tunnels[device_id] = {
                    "public_url": public_url,
                    "local_port": local_port,
                    "local_ip": local_ip,
                    "process": process
                }
                logger.info(f"Created ngrok tunnel for {device_id}: {public_url}")
                return public_url

            try:
                process.terminate()
            except Exception:
                pass
                    
        except Exception as e:
            logger.error(f"Failed to create ngrok tunnel for {device_id}: {e}")
            
        return None
    
    def close_tunnel(self, device_id: str) -> bool:
        """Đóng ngrok tunnel"""
        if device_id in self.active_tunnels:
            tunnel_info = self.active_tunnels[device_id]
            process = tunnel_info.get("process")
            
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    del self.active_tunnels[device_id]
                    logger.info(f"Closed ngrok tunnel for {device_id}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to close tunnel for {device_id}: {e}")
                    
        return False
    
    def update_tunnel_target(self, device_id: str, new_local_ip: str, new_local_port: int) -> Optional[str]:
        """Cập nhật target của tunnel (đóng và tạo mới)"""
        self.close_tunnel(device_id)
        time.sleep(1)
        return self.create_tunnel(device_id, new_local_port, new_local_ip)
    
    def get_device_url(self, device_id: str) -> Optional[str]:
        """Lấy public URL của device"""
        if device_id in self.active_tunnels:
            return self.active_tunnels[device_id]["public_url"]
        return None
    
    def health_check(self) -> Dict[str, bool]:
        """Kiểm tra health của tất cả tunnels"""
        status = {}
        tunnels = self.get_ngrok_tunnels()
        active_ngrok_tunnels = {t.get("name"): t for t in tunnels.get("tunnels", [])}
        
        for device_id, tunnel_info in self.active_tunnels.items():
            tunnel_name = f"mcp_{device_id}"
            if tunnel_name in active_ngrok_tunnels:
                status[device_id] = True
            else:
                status[device_id] = False
                
        return status

# Global instance
ngrok_manager = NgrokManager()
