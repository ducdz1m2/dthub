"""
WebSocket consumers cho AI Hub
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from django.utils import timezone
from .models import ChatSession, ChatMessage, ESP32Device, SensorData
from django.contrib.auth import get_user_model

User = get_user_model()

class RAGMCPConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer cho RAG-MCP chat"""
    
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("rag_mcp_chat", self.channel_name)
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("rag_mcp_chat", self.channel_name)
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        query = data.get("query", "")
        
        # Import here to avoid circular import
        from .rag_mcp_integration import rag_mcp_service
        
        # Use the new streaming function
        await rag_mcp_service.process_websocket_query(self, query)

class SensorDashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer cho real-time sensor dashboard"""
    
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("sensor_dashboard", self.channel_name)
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("sensor_dashboard", self.channel_name)
    
    async def sensor_data(self, event):
        """Handle sensor data broadcast"""
        await self.send(text_data=json.dumps(event))
