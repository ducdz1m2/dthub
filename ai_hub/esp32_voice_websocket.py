"""
ESP32 WebSocket Voice Streaming Code cho DTHub
Tương thích với WebSocket server tại ws://server_ip:8000/ws/voice/
"""

import machine
import network
import time
import json
import uasyncio as asyncio
from umqtt.simple import MQTTClient
from machine import Pin, ADC
import urequests

# Cấu hình WiFi
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# Cấu hình WebSocket server
WEBSOCKET_SERVER = "YOUR_SERVER_IP"  # IP của máy tính chạy DTHub
WEBSOCKET_PORT = 8000
WEBSOCKET_PATH = "/ws/voice/"

# Pin configuration
DHT_PIN = 4
LED_PIN = 2
RELAY_PIN = 5
LIGHT_SENSOR_PIN = 34
SOIL_MOISTURE_PIN = 35
MICROPHONE_PIN = 36  # ADC pin cho microphone

# Initialize components
led = Pin(LED_PIN, Pin.OUT)
relay = Pin(RELAY_PIN, Pin.OUT)
light_adc = ADC(Pin(LIGHT_SENSOR_PIN))
soil_adc = ADC(Pin(SOIL_MOISTURE_PIN))
mic_adc = ADC(Pin(MICROPHONE_PIN))

# Configure ADC for microphone
mic_adc.atten(mic_adc.ATTN_11DB)  # 0-3.6V range

# Global variables
websocket = None
is_connected = False
recording = False
audio_buffer = bytearray()

class ESP32VoiceDevice:
    def __init__(self):
        self.device_id = "esp32_voice_001"
        self.wifi_connected = False
        self.websocket_connected = False
        
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
    
    async def connect_websocket(self):
        """Kết nối WebSocket server"""
        global websocket, is_connected
        
        try:
            import uwebsockets
            
            ws_url = f"ws://{WEBSOCKET_SERVER}:{WEBSOCKET_PORT}{WEBSOCKET_PATH}"
            print(f"Connecting to WebSocket: {ws_url}")
            
            websocket = await uwebsockets.connect(ws_url)
            is_connected = True
            self.websocket_connected = True
            print("[OK] WebSocket connected!")
            
            # Start message listener
            asyncio.create_task(self.websocket_listener())
            return True
            
        except Exception as e:
            print(f"[FAIL] WebSocket connection failed: {e}")
            is_connected = False
            self.websocket_connected = False
            return False
    
    async def websocket_listener(self):
        """Lắng nghe messages từ WebSocket server"""
        global websocket, is_connected
        
        try:
            while is_connected and websocket:
                message = await websocket.recv()
                
                if isinstance(message, str):
                    # Handle text messages (commands, errors)
                    if message == "END_STREAM":
                        print("[OK] Nhận được END_STREAM - phát xong")
                        led.off()  # Tắt LED khi phát xong
                    
                    elif message.startswith("ERROR:"):
                        print(f"[FAIL] Lỗi từ server: {message}")
                        led.off()
                        
                elif isinstance(message, bytes):
                    # Handle audio data - phát ra loa
                    await self.play_audio_chunk(message)
                    
        except Exception as e:
            print(f"[FAIL] WebSocket listener error: {e}")
            is_connected = False
            self.websocket_connected = False
    
    async def play_audio_chunk(self, audio_chunk):
        """Phát audio chunk ra loa (simplified)"""
        try:
            # ESP32 không có built-in DAC chất lượng cao, 
            # đây là simplified version dùng PWM
            # Trong thực tế cần I2S DAC để chất lượng tốt hơn
            
            # Blink LED để indicate đang phát
            led.on()
            
            # Simple PWM audio output (chỉ cho demo)
            # Cần I2S module cho audio chất lượng cao
            await asyncio.sleep(0.01)  # Simulate audio playback time
            
        except Exception as e:
            print(f"[FAIL] Audio playback error: {e}")
    
    async def start_recording(self):
        """Bắt đầu ghi âm"""
        global recording, audio_buffer
        
        if not is_connected:
            print("[FAIL] Chưa kết nối WebSocket")
            return
        
        print("[MIC] Bắt đầu ghi âm...")
        recording = True
        audio_buffer = bytearray()
        
        # Gửi signal bắt đầu recording
        await websocket.send("START_STREAM")
        
        # Start recording loop
        asyncio.create_task(self.record_audio_loop())
    
    async def stop_recording(self):
        """Dừng ghi âm"""
        global recording
        
        if not recording or not is_connected:
            return
        
        print("[STOP] Dừng ghi âm...")
        recording = False
        
        # Gửi signal dừng recording
        await websocket.send("STOP_STREAM")
    
    async def record_audio_loop(self):
        """Loop ghi âm audio từ microphone"""
        global recording, audio_buffer
        
        sample_rate = 16000  # 16kHz
        sample_interval = 1.0 / sample_rate
        
        while recording and is_connected:
            try:
                # Read sample từ ADC
                sample_value = mic_adc.read()
                
                # Convert 12-bit ADC to 8-bit audio sample
                audio_sample = bytes([sample_value >> 4])
                
                # Add to buffer
                audio_buffer.extend(audio_sample)
                
                # Send chunk mỗi 100ms để giảm latency
                if len(audio_buffer) >= 1600:  # 100ms @ 16kHz
                    await websocket.send(audio_buffer)
                    audio_buffer = bytearray()
                
                await asyncio.sleep(sample_interval)
                
            except Exception as e:
                print(f"[FAIL] Recording error: {e}")
                break
    
    async def voice_interaction_loop(self):
        """Main loop cho voice interaction"""
        print("[MIC] Voice interaction ready - Press button to talk")
        
        while True:
            try:
                # Simple button trigger (sử dụng built-in button)
                # Trong thực tế cần nút physical
                
                # Demo: tự động recording mỗi 10 giây để test
                await asyncio.sleep(10)
                
                if is_connected:
                    print("[MIC] Demo auto recording...")
                    await self.start_recording()
                    await asyncio.sleep(3)  # Record 3 giây
                    await self.stop_recording()
                
            except Exception as e:
                print(f"[FAIL] Voice interaction error: {e}")
                await asyncio.sleep(5)
    
    async def main_loop(self):
        """Main async loop"""
        print("[RKT] Starting ESP32 Voice Device...")
        
        # Connect WiFi
        if not self.connect_wifi():
            print("[FAIL] Failed to connect WiFi. Restarting...")
            time.sleep(5)
            machine.reset()
        
        # Connect WebSocket
        while not self.websocket_connected:
            if await self.connect_websocket():
                break
            print("[RTRY] Retrying WebSocket connection in 5 seconds...")
            await asyncio.sleep(5)
        
        # Start voice interaction
        await self.voice_interaction_loop()

def main():
    """Main function"""
    device = ESP32VoiceDevice()
    
    try:
        asyncio.run(device.main_loop())
    except KeyboardInterrupt:
        print("Device stopped by user")
    except Exception as e:
        print(f"[FAIL] Fatal error: {e}")
        machine.reset()

if __name__ == "__main__":
    main()
