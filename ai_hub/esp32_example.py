"""
ESP32 Code Example cho DTHub Integration
Code này chạy trên ESP32 để kết nối với MQTT và tương tác với RAG-MCP
"""

import machine
import network
import time
import json
import dht
import uasyncio as asyncio
from umqtt.simple import MQTTClient
from machine import Pin, ADC

# Cấu hình
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
MQTT_BROKER = "YOUR_MQTT_BROKER_IP"  # IP của server Django
MQTT_PORT = 1883
DEVICE_ID = "esp32_001"  # Unique ID cho device

# Pin configuration
DHT_PIN = 4
LED_PIN = 2
RELAY_PIN = 5
LIGHT_SENSOR_PIN = 34
SOIL_MOISTURE_PIN = 35

# Initialize components
dht_sensor = dht.DHT22(Pin(DHT_PIN))
led = Pin(LED_PIN, Pin.OUT)
relay = Pin(RELAY_PIN, Pin.OUT)
light_adc = ADC(Pin(LIGHT_SENSOR_PIN))
soil_adc = ADC(Pin(SOIL_MOISTURE_PIN))

# Global variables
mqtt_client = None
device_state = {
    "led": "off",
    "relay": "off",
    "last_sensor_read": 0
}

class ESP32Device:
    def __init__(self):
        self.device_id = DEVICE_ID
        self.wifi_connected = False
        self.mqtt_connected = False
        
    def connect_wifi(self):
        """Kết nối WiFi"""
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        if not wlan.isconnected():
            print(f"Connecting to WiFi: {WIFI_SSID}")
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            
            # Wait for connection
            max_wait = 20
            while max_wait > 0:
                if wlan.status() < 0 or wlan.isconnected():
                    break
                max_wait -= 1
                print(".")
                time.sleep(1)
            
            if wlan.isconnected():
                self.wifi_connected = True
                ip = wlan.ifconfig()[0]
                print(f"WiFi connected! IP: {ip}")
                return True
            else:
                print("WiFi connection failed")
                return False
        else:
            self.wifi_connected = True
            return True
    
    def setup_mqtt(self):
        """Setup MQTT client"""
        global mqtt_client
        
        def mqtt_callback(topic, msg):
            """Callback khi nhận MQTT message"""
            try:
                topic_str = topic.decode()
                msg_str = msg.decode()
                print(f"Received: {topic_str} -> {msg_str}")
                
                # Parse topic
                topic_parts = topic_str.split('/')
                if len(topic_parts) >= 3:
                    message_type = topic_parts[2]
                    
                    if message_type == "commands":
                        self.handle_command(msg_str)
                    elif message_type == "response":
                        print(f"LLM Response: {msg_str}")
                        
            except Exception as e:
                print(f"MQTT callback error: {e}")
        
        try:
            mqtt_client = MQTTClient(
                client_id=self.device_id.encode(),
                server=MQTT_BROKER,
                port=MQTT_PORT
            )
            mqtt_client.set_callback(mqtt_callback)
            mqtt_client.connect()
            
            # Subscribe to topics
            mqtt_client.subscribe(f"esp32/{self.device_id}/commands")
            mqtt_client.subscribe(f"esp32/{self.device_id}/response")
            
            self.mqtt_connected = True
            print("MQTT connected!")
            return True
            
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            return False
    
    def handle_command(self, msg_str):
        """Xử lý command từ server"""
        try:
            data = json.loads(msg_str)
            command = data.get("command", "")
            parameters = data.get("parameters", {})
            command_id = data.get("command_id")
            
            print(f"Executing command: {command}")
            
            if command == "toggle_led":
                self.toggle_led()
                self.send_command_response(command_id, "LED toggled")
                
            elif command == "toggle_relay":
                self.toggle_relay()
                self.send_command_response(command_id, "Relay toggled")
                
            elif command == "read_sensors":
                sensor_data = self.read_sensors()
                self.send_sensor_data(sensor_data)
                self.send_command_response(command_id, "Sensors read")
                
            elif command == "ask_llm":
                query = parameters.get("query", "")
                self.ask_llm(query)
                
            else:
                print(f"Unknown command: {command}")
                
        except Exception as e:
            print(f"Command handling error: {e}")
    
    def toggle_led(self):
        """Toggle LED"""
        current_state = device_state["led"]
        new_state = "off" if current_state == "on" else "on"
        device_state["led"] = new_state
        led.value(1 if new_state == "on" else 0)
        print(f"LED: {new_state}")
    
    def toggle_relay(self):
        """Toggle Relay"""
        current_state = device_state["relay"]
        new_state = "off" if current_state == "on" else "on"
        device_state["relay"] = new_state
        relay.value(1 if new_state == "on" else 0)
        print(f"Relay: {new_state}")
    
    def read_sensors(self):
        """Đọc tất cả sensors"""
        try:
            # Read DHT22
            dht_sensor.measure()
            temperature = dht_sensor.temperature()
            humidity = dht_sensor.humidity()
            
            # Read light sensor
            light_value = light_adc.read()
            light_percent = int((light_value / 4095) * 100)
            
            # Read soil moisture
            soil_value = soil_adc.read()
            soil_percent = int((1 - soil_value / 4095) * 100)
            
            sensor_data = {
                "temperature": round(temperature, 1),
                "humidity": round(humidity, 1),
                "light": light_percent,
                "soil_moisture": soil_percent,
                "timestamp": time.time()
            }
            
            print(f"Sensor data: {sensor_data}")
            return sensor_data
            
        except Exception as e:
            print(f"Sensor reading error: {e}")
            return {}
    
    def send_sensor_data(self, sensor_data):
        """Gửi sensor data qua MQTT"""
        if mqtt_client and sensor_data:
            topic = f"esp32/{self.device_id}/sensor_data"
            mqtt_client.publish(topic, json.dumps(sensor_data))
            print(f"Published sensor data to {topic}")
    
    def send_command_response(self, command_id, message):
        """Gửi response cho command"""
        if mqtt_client:
            topic = f"esp32/{self.device_id}/command_response"
            response = {
                "command_id": command_id,
                "message": message,
                "timestamp": time.time()
            }
            mqtt_client.publish(topic, json.dumps(response))
    
    def ask_llm(self, query):
        """Gửi query đến LLM qua MQTT"""
        if mqtt_client:
            topic = f"esp32/{self.device_id}/request"
            request_data = {
                "query": query,
                "timestamp": time.time()
            }
            mqtt_client.publish(topic, json.dumps(request_data))
            print(f"Sent LLM request: {query}")
    
    async def main_loop(self):
        """Main async loop"""
        print("Starting main loop...")
        
        while True:
            try:
                # Check MQTT messages
                if mqtt_client:
                    mqtt_client.check_msg()
                
                # Read sensors every 30 seconds
                current_time = time.time()
                if current_time - device_state["last_sensor_read"] > 30:
                    sensor_data = self.read_sensors()
                    self.send_sensor_data(sensor_data)
                    device_state["last_sensor_read"] = current_time
                
                # Blink LED to show device is alive
                led.on()
                await asyncio.sleep(0.1)
                led.off()
                
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Main loop error: {e}")
                await asyncio.sleep(10)

def main():
    """Main function"""
    device = ESP32Device()
    
    # Connect WiFi
    if not device.connect_wifi():
        print("Failed to connect WiFi. Restarting...")
        time.sleep(5)
        machine.reset()
    
    # Setup MQTT
    if not device.setup_mqtt():
        print("Failed to setup MQTT. Restarting...")
        time.sleep(5)
        machine.reset()
    
    # Send initial status
    status_data = {
        "device_id": device.device_id,
        "status": "online",
        "timestamp": time.time()
    }
    mqtt_client.publish(f"esp32/{device.device_id}/status", json.dumps(status_data))
    
    # Start async main loop
    try:
        asyncio.run(device.main_loop())
    except KeyboardInterrupt:
        print("Device stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        machine.reset()

if __name__ == "__main__":
    main()
