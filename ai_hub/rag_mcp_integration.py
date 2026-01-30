"""
RAG-MCP Integration cho DTHub AI Hub
Tích hợp RAG system với Django và ESP32/MQTT
"""

import os
import json
import asyncio
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
import time

# Import từ RAG-MCP system
import sys
import os
# Get the rag-mcp directory path (parent of dthub)
rag_mcp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag-mcp')
sys.path.append(rag_mcp_path)

# Mock MQTT cho testing
class MockMQTTClient:
    def __init__(self):
        self.connected = False
        
    def connect(self, host, port, keepalive):
        self.connected = True
        print(f"🔌 Mock MQTT connected to {host}:{port}")
        
    def loop_start(self):
        pass
        
    def subscribe(self, topic):
        print(f"📡 Subscribed to: {topic}")
        
    def publish(self, topic, payload):
        print(f"📤 Published to {topic}: {payload[:100]}...")

# Try import paho-mqtt, use mock if not available
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    mqtt = None

from main import MCPDispatcher
from database import load_db

class RAGMCPService:
    """Service chính cho RAG-MCP integration"""
    
    def __init__(self):
        self.dispatcher = MCPDispatcher()
        self.vectorstore = None
        self.retriever = None
        self.mqtt_client = None
        self.channel_layer = get_channel_layer()
        
        # Load RAG database
        self._load_rag_db()
        
        # Setup MQTT
        self._setup_mqtt()
    
    def _load_rag_db(self):
        """Load RAG database"""
        try:
            self.vectorstore = load_db()
            self.retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": 3, "fetch_k": 8}
            )
            print("✅ RAG Database loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load RAG DB: {e}")
    
    def _setup_mqtt(self):
        """Setup MQTT client cho ESP32 communication"""
        try:
            # Use real MQTT if available, otherwise use mock
            if MQTT_AVAILABLE:
                self.mqtt_client = mqtt.Client()
                self.mqtt_client.on_connect = self._on_mqtt_connect
                self.mqtt_client.on_message = self._on_mqtt_message
            else:
                self.mqtt_client = MockMQTTClient()
                print("⚠️ Using Mock MQTT (paho-mqtt not available)")
            
            # Connect to MQTT broker (localhost hoặc external)
            mqtt_host = getattr(settings, 'MQTT_HOST', 'localhost')
            mqtt_port = getattr(settings, 'MQTT_PORT', 1883)
            
            self.mqtt_client.connect(mqtt_host, mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            print("✅ MQTT client connected")
        except Exception as e:
            print(f"❌ MQTT setup failed: {e}")
            # Fallback to mock MQTT
            self.mqtt_client = MockMQTTClient()
            print("🔌 Fallback to Mock MQTT")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback khi MQTT kết nối"""
        print(f"MQTT Connected with result code {rc}")
        
        # Subscribe đến ESP32 topics
        client.subscribe("esp32/+/sensor_data")
        client.subscribe("esp32/+/request")
        client.subscribe("esp32/+/status")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Callback khi nhận MQTT message"""
        try:
            topic_parts = msg.topic.split('/')
            device_id = topic_parts[1]
            message_type = topic_parts[2]
            
            payload = json.loads(msg.payload.decode())
            
            if message_type == "request":
                # ESP32 request đến LLM
                self._handle_esp32_request(device_id, payload)
            elif message_type == "sensor_data":
                # Lưu sensor data vào database
                self._handle_sensor_data(device_id, payload)
                
        except Exception as e:
            print(f"❌ MQTT message error: {e}")
    
    def _handle_esp32_request(self, device_id, payload):
        """Xử lý request từ ESP32 - generate response giống như main.py"""
        import ollama
        query = payload.get("query", "")
        
        # Process với RAG-MCP
        selected_tool, confidence = self.dispatcher.smart_route(query)
        
        if selected_tool in self.dispatcher.tools:
            handler = self.dispatcher.tools[selected_tool]["handler"]
            
            if selected_tool == "rag_search":
                prompt = handler(query, self.retriever)
            else:
                prompt = handler(query)
        else:
            prompt = query
        
        # Generate response với ollama - giống như main.py
        try:
            stream = ollama.chat(
                model="qwen2.5:1.5b",
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                options={
                    "temperature": 0.1,
                    "num_predict": 250
                }
            )
            response = stream['message']['content']
        except Exception as e:
            response = f"Lỗi khi gọi LLM: {str(e)}"
        
        # Gửi response qua MQTT
        response_topic = f"esp32/{device_id}/response"
        response_data = {
            "query": query,
            "response": response,
            "tool_used": selected_tool,
            "confidence": confidence,
            "timestamp": time.time()
        }
        
        self.mqtt_client.publish(response_topic, json.dumps(response_data))
    
    def _handle_sensor_data(self, device_id, payload):
        """Xử lý sensor data từ ESP32"""
        # Broadcast qua WebSocket cho real-time dashboard
        asyncio.create_task(
            self.channel_layer.group_send(
                "sensor_dashboard",
                {
                    "type": "sensor_data",
                    "device_id": device_id,
                    "data": payload,
                    "timestamp": time.time()
                }
            )
        )
    
    async def process_websocket_query(self, consumer, query):
        """Xử lý query từ WebSocket - streaming response"""
        import ollama
        print(f"🔥 Starting process_websocket_query for: {query}")
        
        selected_tool, confidence = self.dispatcher.smart_route(query)
        print(f"🔥 Selected tool: {selected_tool}, confidence: {confidence}")
        
        if selected_tool in self.dispatcher.tools:
            handler = self.dispatcher.tools[selected_tool]["handler"]
            
            if selected_tool == "rag_search":
                prompt = handler(query, self.retriever)
            else:
                prompt = handler(query)
        else:
            prompt = query
        
        print(f"🔥 Generated prompt: {prompt[:100]}...")
        
        # Send initial debug message
        await consumer.send(text_data=json.dumps({
            "type": "response",
            "query": query,
            "debug": "Starting ollama chat...",
            "done": False
        }))
        print("🔥 Sent debug message")
        
        # Generate response với ollama - streaming
        try:
            if selected_tool == "general_chat":
                # For general chat, return handler response directly
                response = handler(query)
                await consumer.send(text_data=json.dumps({
                    "type": "response",
                    "query": query,
                    "chunk": response,
                    "done": False
                }))
                await consumer.send(text_data=json.dumps({
                    "type": "response",
                    "query": query,
                    "done": True,
                    "full_response": response,
                    "tool_used": selected_tool,
                    "confidence": confidence,
                    "response_time": 0.1
                }))
            else:
                # Use ollama for other tools with streaming
                stream = ollama.chat(
                    model="qwen2.5:1.5b",
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    options={
                        "temperature": 0.1,
                        "num_predict": 250
                    }
                )
                
                await consumer.send(text_data=json.dumps({
                    "type": "response",
                    "query": query,
                    "debug": "Ollama stream started...",
                    "done": False
                }))
                
                full_response = ""
                chunk_count = 0
                for chunk in stream:
                    content = chunk['message']['content']
                    full_response += content
                    chunk_count += 1
                    
                    print(f"🔥 Sending chunk {chunk_count}: {content}")
                    
                    # Send chunk immediately
                    await consumer.send(text_data=json.dumps({
                        "type": "response",
                        "query": query,
                        "chunk": content,
                        "done": False,
                        "chunk_num": chunk_count
                    }))
                    print(f"🔥 Sent chunk {chunk_count}")
                    
                    # Small delay to allow browser processing
                    if chunk_count % 3 == 0:  # Every 3 chunks
                        import asyncio
                        await asyncio.sleep(0.01)
                
                print(f"🔥 Stream loop completed, sent {chunk_count} chunks")
                
                # Send completion signal
                await consumer.send(text_data=json.dumps({
                    "type": "response",
                    "query": query,
                    "done": True,
                    "full_response": full_response,
                    "tool_used": selected_tool,
                    "confidence": confidence,
                    "response_time": 0.0  # Will be calculated on frontend
                }))
                
        except Exception as e:
            print(f"❌ Error in process_websocket_query: {e}")
            import traceback
            traceback.print_exc()
            await consumer.send(text_data=json.dumps({
                "type": "response",
                "query": query,
                "error": f"Lỗi khi gọi LLM: {str(e)}",
                "done": True
            }))

# Global service instance
rag_mcp_service = RAGMCPService()

class RAGMCPConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer cho RAG-MCP"""
    
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("rag_mcp_chat", self.channel_name)
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("rag_mcp_chat", self.channel_name)
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            query = data.get("query", "")
            print(f"🔥 WebSocket received query: {query}")
            
            # Process với RAG-MCP service
            await rag_mcp_service.process_websocket_query(self, query)
        except Exception as e:
            print(f"❌ WebSocket receive error: {e}")
            import traceback
            traceback.print_exc()
            await self.send(text_data=json.dumps({
                "type": "response",
                "error": f"WebSocket error: {str(e)}",
                "done": True
            }))

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
