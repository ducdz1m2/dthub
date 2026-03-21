"""
WebSocket consumers cho AI Hub
"""

import json
import asyncio
import tempfile
import os
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.conf import settings
from .models import ChatSession, ChatMessage, ESP32Device, SensorData
from django.contrib.auth import get_user_model

User = get_user_model()

class RAGMCPConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer cho RAG-MCP chat"""

    async def connect(self):
        try:
            await self.accept()
            await self.channel_layer.group_add("rag_mcp_chat", self.channel_name)
            # Initialize session_id as None, will be set on first message
            self.session_id = None
            print(f"[OK] RAGMCPConsumer: WebSocket connected ({self.channel_name})")
        except Exception as e:
            print(f"[FAIL] RAGMCPConsumer: Connection error: {e}")
            import traceback
            traceback.print_exc()
            try:
                await self.close(code=4000)
            except:
                pass

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard("rag_mcp_chat", self.channel_name)
            print(f"[FAIL] RAGMCPConsumer: WebSocket disconnected ({close_code})")
        except Exception as e:
            print(f"[FAIL] RAGMCPConsumer: Disconnect error: {e}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            query = data.get("query", "")
            session_id = data.get("session_id", "").strip()

            print(f"[SEARCH] WebSocket DEBUG: Received message: {query[:50]}...")

            # Generate UUID if session_id is empty or not provided
            if not session_id:
                if not self.session_id:
                    self.session_id = str(uuid.uuid4())
                    print(f"[ID] Generated new session_id: {self.session_id}")
                session_id = self.session_id
            else:
                # Update stored session_id if provided
                self.session_id = session_id
                print(f"[MSG] Using session_id: {session_id}")

            # Import here to avoid circular import
            from .rag_mcp_integration import rag_mcp_service

            # Use the streaming function with better error handling
            try:
                await rag_mcp_service.process_websocket_query(self, query, session_id)
            except Exception as e:
                print(f"[FAIL] Error in process_websocket_query: {e}")
                import traceback
                traceback.print_exc()
                # Send error response but keep connection open
                await self.send(text_data=json.dumps({
                    "type": "response",
                    "error": f"Có lỗi khi xử lý: {str(e)}",
                    "full_response": f"Xin lỗi, tôi gặp lỗi khi xử lý yêu cầu của bạn: {str(e)}",
                    "done": True,
                    "tool_used": "error",
                    "response_time": 0.0
                }, ensure_ascii=False))

        except json.JSONDecodeError as e:
            print(f"[FAIL] JSON Decode Error: {e}")
            await self.send(text_data=json.dumps({
                "type": "response",
                "error": "Dữ liệu gửi đi không hợp lệ (JSON format error)",
                "done": True
            }, ensure_ascii=False))
        except Exception as e:
            print(f"[FAIL] WebSocket receive error: {e}")
            import traceback
            traceback.print_exc()
            # Send error but keep connection alive
            await self.send(text_data=json.dumps({
                "type": "response",
                "error": f"Lỗi WebSocket: {str(e)}",
                "full_response": "Xin lỗi, có lỗi kết nối. Vui lòng thử lại.",
                "done": True,
                "tool_used": "websocket_error"
            }, ensure_ascii=False))

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

class VoiceStreamConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer cho voice streaming ESP32 (Hỗ trợ Hybrid Session)"""
    
    async def connect(self):
        # 1. LẤY TOKEN & SESSION TỪ QUERY STRING
        from urllib.parse import parse_qs
        query_string = self.scope['query_string'].decode('utf-8')
        params = parse_qs(query_string)
        
        token = params.get('token', [None])[0]
        session_id = params.get('session_id', [None])[0]
        
        # 2. XÁC THỰC THIẾT BỊ
        if not token:
            print("[FAIL] VoiceStreamConsumer: Thiếu token xác thực")
            await self.close(code=4001)
            return
            
        device = await sync_to_async(ESP32Device.objects.filter(auth_token=token, is_active=True).first)()
        if not device:
            print(f"[FAIL] VoiceStreamConsumer: Token không hợp lệ: {token}")
            await self.close(code=4002)
            return
            
        self.device = device
        self.session_id = session_id
        
        await self.accept()
        print(f"\n[+] ESP32 '{device.name}' đã kết nối thành công (Session: {session_id})")
        self.audio_buffer = bytearray()
        self.is_recording = False
        
        # Load STT và TTS engines
        await self.load_voice_engines()
    
    async def disconnect(self, close_code):
        print(f"[-] ESP32 đã ngắt kết nối: {close_code}")
    
    async def receive(self, text_data=None, bytes_data=None):
        """Xử lý dữ liệu nhận được từ ESP32"""
        
        # Cập nhật last_seen mỗi khi nhận được dữ liệu từ thiết bị
        if hasattr(self, 'device'):
            await sync_to_async(ESP32Device.objects.filter(id=self.device.id).update)(last_seen=timezone.now())

        # Xử lý các lệnh điều khiển (Text) từ ESP32
        if text_data:
            message = text_data
            if message == "START_STREAM":
                print("[MIC] Khách hàng đang nói...")
                self.audio_buffer.clear()  # Xóa bộ đệm cũ chuẩn bị ghi phiên mới
                self.is_recording = True
            
            elif message == "STOP_STREAM":
                print(f"[STOP] Đã ngừng nói. Nhận được tổng cộng {len(self.audio_buffer)} bytes.")
                self.is_recording = False
                
                if len(self.audio_buffer) > 0:
                    await self.process_voice_audio()
        
        # Xử lý luồng âm thanh thô (Binary) từ ESP32
        elif bytes_data:
            if self.is_recording:
                self.audio_buffer.extend(bytes_data)
    
    async def load_voice_engines(self):
        """Load STT và TTS engines"""
        try:
            # Load STT engine
            import speech_recognition as sr
            self.stt_engine = sr.Recognizer()
            print("[OK] STT engine loaded")
        except Exception as e:
            print(f"[FAIL] Failed to load STT: {e}")
            self.stt_engine = None
        
        try:
            # Load TTS engine
            from gtts import gTTS
            self.tts_model = gTTS
            print("[OK] TTS engine loaded")
        except Exception as e:
            print(f"[FAIL] Failed to load TTS: {e}")
            self.tts_model = None
    
    async def process_voice_audio(self):
        """Xử lý audio: STT -> RAG-MCP -> TTS -> Stream về ESP32"""
        try:
            print("[AUDIO] Đang xử lý audio...")
            
            # 1. Speech-to-Text
            text = await self.speech_to_text()
            if not text:
                await self.send("ERROR: Speech recognition failed")
                return
            
            print(f"[MSG] Nhận dạng được: {text}")
            
            # 2. Xử lý qua RAG-MCP Service (Sử dụng chung logic với Chat & API)
            from .rag_mcp_integration import rag_mcp_service
            
            # Gửi tín hiệu đang suy nghĩ cho ESP32 (đổi màu mắt)
            await self.send("WAITING") 
            
            # Gọi service xử lý (Hàm này đã được nâng cấp để trả về full_response và lưu DB)
            response = await rag_mcp_service.process_websocket_query(self, text, self.session_id)
            print(f"[AI] Response: {response}")
            
            # 3. Text-to-Speech và stream về ESP32
            if response:
                await self.text_to_speech_stream(response)
            else:
                await self.send("ERROR: No response from AI")
        
        except Exception as e:
            print(f"[FAIL] Lỗi xử lý audio: {e}")
            await self.send(f"ERROR: {str(e)}")
    
    async def speech_to_text(self):
        """Convert audio buffer to text"""
        if not self.stt_engine or len(self.audio_buffer) == 0:
            return None
        
        try:
            # 1. Lấy cấu hình STT của user
            from .models import AIConfiguration
            user_id = self.device.user_id if hasattr(self, 'device') and self.device else None
            
            @sync_to_async
            def get_config(u_id):
                config = AIConfiguration.objects.filter(user_id=u_id, is_default=True, is_active=True).first()
                if not config:
                    config = AIConfiguration.objects.filter(user__isnull=True, is_default=True, is_active=True).first()
                return config
            
            ai_config = await get_config(user_id)
            language = ai_config.stt_language if ai_config else 'vi-VN'
            engine = ai_config.stt_engine if ai_config else 'vosk'

            # 2. Tạo file WAV từ buffer
            try:
                from pydub import AudioSegment
                raw_audio = AudioSegment(
                    data=self.audio_buffer,
                    sample_width=2, frame_rate=16000, channels=1
                )
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    wav_path = temp_file.name
                raw_audio.export(wav_path, format='wav')
            except Exception as e:
                print(f"[FAIL] PyDub conversion failed: {e}")
                wav_path = self.create_wav_from_raw()
                if not wav_path: return "xin chào"

            # 3. Gọi Voice Microservice (Port 5002)
            text = None
            try:
                url = "http://127.0.0.1:5002/stt"
                with open(wav_path, 'rb') as f:
                    files = {'audio': f}
                    data = {'language': language, 'engine': engine}
                    response = requests.post(url, files=files, data=data, timeout=10)
                
                if response.status_code == 200:
                    text = response.json().get('text', '')
            except Exception as e:
                print(f"[FAIL] Connection to Voice Service failed: {e}")
                # Fallback to local STT logic if service is down
                pass

            # Clean up
            if os.path.exists(wav_path): os.unlink(wav_path)
            
            if text:
                print(f"[OK] STT Result ({engine}): {text}")
                return text.lower()
            return "xin chào"
            
        except Exception as e:
            print(f"[FAIL] STT General Error: {e}")
            return "xin chào"
    
    def create_wav_from_raw(self):
        """Create simple WAV file from raw PCM data"""
        try:
            import struct
            
            # WAV file header for 16-bit PCM, 16kHz, mono
            sample_rate = 16000
            channels = 1
            bits_per_sample = 16
            byte_rate = sample_rate * channels * bits_per_sample // 8
            block_align = channels * bits_per_sample // 8
            
            data_size = len(self.audio_buffer)
            file_size = 36 + data_size
            
            # Create WAV header
            header = struct.pack('<4sL4s', b'RIFF', file_size, b'WAVE')
            fmt_chunk = struct.pack('<4sLHHLHH', b'fmt ', 16, 1, channels, sample_rate, byte_rate, block_align, bits_per_sample)
            data_chunk = struct.pack('<4sL', b'data', data_size)
            
            # Write to temp file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(header + fmt_chunk + data_chunk + self.audio_buffer)
                return temp_file.name
                
        except Exception as e:
            print(f"[FAIL] WAV creation failed: {e}")
            return None
    
    async def text_to_speech_stream(self, text):
        """Convert text to speech, chuyển sang RAW PCM và stream về ESP32"""
        try:
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')
            elif not isinstance(text, str):
                text = str(text)
            
            print(f"[TXT] TTS Input text: {text}")
            
            # Lấy cấu hình AI của User
            from .models import AIConfiguration
            user_id = self.device.user_id if hasattr(self, 'device') and self.device else None
            
            @sync_to_async
            def get_config(u_id):
                config = AIConfiguration.objects.filter(user_id=u_id, is_default=True, is_active=True).first()
                if not config:
                    config = AIConfiguration.objects.filter(user__isnull=True, is_default=True, is_active=True).first()
                return config
            
            ai_config = await get_config(user_id)
            tts_engine = getattr(ai_config, 'tts_engine', 'local')
            tts_lang = ai_config.tts_voice if ai_config else 'vi'
            tts_speed = ai_config.tts_speed if ai_config else 1.0
            tts_custom_url = getattr(ai_config, 'tts_custom_url', None)
            
            filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            output_path = os.path.join(settings.MEDIA_ROOT, 'tts', filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 1. Tạo file âm thanh (Local System hoặc Custom API)
            try:
                if tts_engine == 'custom' and tts_custom_url:
                    print(f"[TXT] Gọi Custom TTS API: {tts_custom_url}...")
                    resp = requests.post(tts_custom_url, json={'text': text}, timeout=15)
                    if resp.status_code == 200:
                        with open(output_path, 'wb') as f:
                            f.write(resp.content)
                    else:
                        raise Exception(f"Custom TTS API trả về lỗi: {resp.status_code}")
                else:
                    import pyttsx3
                    print(f"[TXT] Tạo file âm thanh Local System (lang={tts_lang})...")
                    # Sử dụng pyttsx3 để lưu ra file
                    engine = pyttsx3.init()
                    voices = engine.getProperty('voices')
                    for voice in voices:
                        if tts_lang in voice.languages or tts_lang in voice.id.lower():
                            engine.setProperty('voice', voice.id)
                            break
                    engine.setProperty('rate', int(200 * tts_speed))
                    engine.save_to_file(text, output_path)
                    engine.runAndWait()
            except Exception as tts_error:
                print(f"[FAIL] Local TTS Error: {tts_error}")
                await self.send(text_data=f"ERROR: Local TTS failed - {str(tts_error)}")
                return
            
            # 2. CHUYỂN ĐỔI MP3 SANG RAW PCM (Bắt buộc cho ESP32)
            try:
                from pydub import AudioSegment
                print("[CFG] Chuyển đổi MP3 sang định dạng ESP32 (RAW PCM, 16kHz, Mono, 16-bit)...")
                audio = AudioSegment.from_mp3(output_path)
                
                # Điều chỉnh tốc độ nếu cần
                if tts_speed != 1.0:
                    print(f"[CFG] Điều chỉnh tốc độ đọc: {tts_speed}x")
                    new_sample_rate = int(audio.frame_rate * tts_speed)
                    audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_sample_rate})
                    audio = audio.set_frame_rate(16000) # Reset lại về 16kHz cho ESP32
                
                # Ép thông số khớp 100% với cấu hình I2S trên mạch
                audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                
                # Lấy dữ liệu RAW PCM thô (Không lấy header)
                raw_pcm_data = audio.raw_data
                print(f"[AUDIO] Kích thước RAW PCM: {len(raw_pcm_data)} bytes")
                
                # 3. STREAM DỮ LIỆU VỀ ESP32 TRONG CÁC CHUNK NHỎ (1024 bytes)
                CHUNK_SIZE = 1024
                for i in range(0, len(raw_pcm_data), CHUNK_SIZE):
                    chunk = raw_pcm_data[i:i + CHUNK_SIZE]
                    await self.send(bytes_data=chunk)
                    # Chờ một chút để tránh làm nghẽn buffer của ESP32 (16kHz, 16bit = 32000 bytes/sec)
                    # 1024 bytes = ~32ms of audio
                    await asyncio.sleep(0.02) # Gửi nhanh hơn thực tế 1 chút (20ms)
                
                # Gửi tín hiệu kết thúc stream
                await self.send(text_data="END_STREAM")
                print("[OK] Đã stream xong audio về ESP32")

                # Xóa file MP3 tạm
                if os.path.exists(output_path):
                    os.unlink(output_path)

            except Exception as pydub_err:
                print(f"[FAIL] Lỗi convert audio: {pydub_err}")
                await self.send(text_data=f"ERROR: Audio conversion failed - {str(pydub_err)}")
                return
            
        except Exception as e:
            print(f"[FAIL] Lỗi tổng quát TTS: {e}")
            await self.send(text_data=f"ERROR: General TTS failure")