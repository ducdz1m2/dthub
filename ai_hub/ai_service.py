"""
AI Service - Tích hợp nhiều AI providers và engines
Hỗ trợ: Ollama, OpenAI, Gemini, Claude cho LLM
         Google Speech, Whisper, Azure cho STT
         gTTS, Azure, ElevenLabs cho TTS
"""

import os
import json
import time
import requests
import tempfile
from typing import Optional, Dict, Any
from django.conf import settings
from .models import AIConfiguration

class AIService:
    """Service chính để xử lý AI operations dựa trên configuration"""
    
    def __init__(self, config: AIConfiguration = None):
        self.config = config
        if not config:
            # Lấy config mặc định
            self.config = self.get_default_config()
    
    @staticmethod
    def get_default_config() -> Optional[AIConfiguration]:
        """Lấy AI Configuration mặc định"""
        # Ưu tiên: global default > first active
        config = AIConfiguration.objects.filter(
            user__isnull=True, 
            is_default=True, 
            is_active=True
        ).first()
        
        if not config:
            config = AIConfiguration.objects.filter(is_active=True).first()
        
        return config
    
    # --- LLM METHODS ---
    
    def chat_completion(self, messages: list, **kwargs) -> str:
        """Gọi LLM (chỉ Ollama)"""
        if not self.config:
            raise ValueError("No AI configuration available")
        
        # Chỉ hỗ trợ Ollama
        return self._ollama_chat(messages, **kwargs)
    
    def _ollama_chat(self, messages: list, **kwargs) -> str:
        """Ollama chat completion"""
        try:
            import ollama
            
            response = ollama.chat(
                model=self.config.llm_model,
                messages=messages,
                stream=False,
                options={
                    "temperature": self.config.llm_temperature,
                    "num_predict": self.config.llm_max_tokens
                }
            )
            return response['message']['content']
            
        except ImportError:
            raise ImportError("Ollama library not installed. Run: pip install ollama")
        except Exception as e:
            raise Exception(f"Ollama error: {str(e)}")
    
    # --- STT METHODS ---
    
    def speech_to_text(self, audio_file) -> str:
        """Chuyển speech thành text bằng Voice Microservice (Port 5002)"""
        if not self.config:
            raise ValueError("No AI configuration available")
        
        # Microservice URL
        url = "http://127.0.0.1:5002/stt"
        
        try:
            # Gửi file đến microservice
            files = {'audio': audio_file}
            data = {
                'language': self.config.stt_language,
                'engine': self.config.stt_engine
            }
            
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('text', '').lower()
            else:
                # Fallback nếu microservice chưa chạy hoặc lỗi
                print(f"[WARN] Voice Service error: {response.status_code}. Falling back to legacy STT.")
                return self._legacy_stt(audio_file)
                
        except Exception as e:
            print(f"[ERROR] Connection to Voice Service failed: {e}")
            return self._legacy_stt(audio_file)

    def _legacy_stt(self, audio_file) -> str:
        """Fallback STT logic if microservice is offline"""
        # Logic cũ của bạn (đã được tối ưu hóa)
        import speech_recognition as sr
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            for chunk in audio_file.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(temp_path) as source:
                audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data, language=self.config.stt_language).lower()
        except:
            return ""
        finally:
            if os.path.exists(temp_path): os.unlink(temp_path)

    # --- RAG METHODS ---

    def rag_search(self, query: str, k: int = 3) -> str:
        """Tìm kiếm kiến thức từ RAG Microservice (Port 5001)"""
        url = "http://127.0.0.1:5001/search"
        try:
            payload = {"query": query, "k": k}
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json().get("result", "")
            return ""
        except Exception as e:
            print(f"[ERROR] RAG Service connection failed: {e}")
            return ""

    # --- TTS METHODS ---
    
    def text_to_speech(self, text: str) -> str:
        """Chuyển text thành speech bằng Voice Microservice (Port 5002)"""
        if not self.config:
            raise ValueError("No AI configuration available")
        
        url = "http://127.0.0.1:5002/tts"
        
        try:
            data = {
                'text': text,
                'voice': self.config.tts_voice,
                'speed': self.config.tts_speed,
                'engine': self.config.tts_engine
            }
            
            response = requests.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                # Lưu file nhận được từ microservice vào media/tts/
                import uuid
                filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
                output_path = os.path.join(settings.MEDIA_ROOT, 'tts', filename)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                return f"{settings.MEDIA_URL}tts/{filename}"
            else:
                return self._local_text_to_speech(text)
                
        except Exception as e:
            print(f"[ERROR] Voice Service connection failed: {e}")
            return self._local_text_to_speech(text)

    def _local_text_to_speech(self, text: str) -> str:
        """Local System Text-to-Speech (pyttsx3)"""
        try:
            import pyttsx3
            import uuid
            
            # Generate unique filename
            filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            output_path = os.path.join(settings.MEDIA_ROOT, 'tts', filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Initialize engine
            engine = pyttsx3.init()
            
            # Configure voice based on language
            voices = engine.getProperty('voices')
            lang = self.config.tts_voice # 'vi', 'en', 'ja'
            
            # Tìm giọng đọc phù hợp trong hệ thống
            selected_voice = None
            for voice in voices:
                if lang in voice.languages or lang in voice.id.lower():
                    selected_voice = voice.id
                    break
            
            if selected_voice:
                engine.setProperty('voice', selected_voice)
            
            # Set speed
            speed = getattr(self.config, 'tts_speed', 1.0)
            engine.setProperty('rate', int(200 * speed)) # 200 is default rate
            
            # Save to file
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            
            # Return URL
            return f"{settings.MEDIA_URL}tts/{filename}"
            
        except ImportError:
            raise ImportError("pyttsx3 library not installed. Run: pip install pyttsx3")
        except Exception as e:
            raise Exception(f"Local TTS error: {str(e)}")

    def _custom_tts(self, text: str) -> str:
        """Custom TTS API call"""
        try:
            url = self.config.tts_custom_url
            response = requests.post(url, json={'text': text}, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                # Giả sử API trả về URL file audio hoặc data base64
                # Ở đây ta giả định trả về URL
                return data.get('audio_url', '')
            else:
                raise Exception(f"Custom TTS API error: {response.status_code}")
        except Exception as e:
            raise Exception(f"Custom TTS error: {str(e)}")
    
    def _gtts_text_to_speech(self, text: str) -> str:
        """Google Text-to-Speech"""
        try:
            from gtts import gTTS
            import uuid
            
            # Generate unique filename
            filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            output_path = os.path.join(settings.MEDIA_ROOT, 'tts', filename)
            
            # Create tts directory if not exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Generate speech
            tts = gTTS(
                text=text, 
                lang=self.config.tts_voice, 
                slow=False
            )
            tts.save(output_path)
            
            # Adjust speed if needed using pydub
            if hasattr(self.config, 'tts_speed') and self.config.tts_speed != 1.0:
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_mp3(output_path)
                    # Change playback speed without changing pitch
                    new_sample_rate = int(audio.frame_rate * self.config.tts_speed)
                    faster_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_sample_rate})
                    faster_audio = faster_audio.set_frame_rate(audio.frame_rate)
                    faster_audio.export(output_path, format="mp3")
                except Exception as speed_err:
                    print(f"Error adjusting TTS speed: {speed_err}")
            
            # Return URL
            return f"{settings.MEDIA_URL}tts/{filename}"
            
        except ImportError:
            raise ImportError("gTTS library not installed. Run: pip install gtts")
        except Exception as e:
            raise Exception(f"gTTS error: {str(e)}")

# --- Utility Functions ---

def get_ai_service(user=None) -> AIService:
    """Get AI service instance for user"""
    config = None
    if user and not user.is_anonymous:
        # Try to get user-specific config
        config = AIConfiguration.objects.filter(
            user=user,
            is_default=True,
            is_active=True
        ).first()
    
    # Fallback to default config
    if not config:
        config = AIService.get_default_config()
    
    return AIService(config)

def test_ai_config(config: AIConfiguration) -> Dict[str, Any]:
    """Test AI configuration"""
    results = {
        'llm': {'status': 'unknown', 'message': ''},
        'stt': {'status': 'unknown', 'message': ''},
        'tts': {'status': 'unknown', 'message': ''}
    }
    
    ai_service = AIService(config)
    
    # Test LLM
    try:
        response = ai_service.chat_completion([
            {"role": "user", "content": "Hello, respond with 'OK'"}
        ])
        if 'OK' in response or 'ok' in response.lower():
            results['llm'] = {'status': 'success', 'message': 'LLM working correctly'}
        else:
            results['llm'] = {'status': 'warning', 'message': f'LLM responded but unexpected: {response[:50]}...'}
    except Exception as e:
        results['llm'] = {'status': 'error', 'message': str(e)}
    
    # Test TTS
    try:
        audio_url = ai_service.text_to_speech("Hello world")
        if audio_url and os.path.exists(os.path.join(settings.MEDIA_ROOT, 'tts', os.path.basename(audio_url))):
            results['tts'] = {'status': 'success', 'message': 'TTS working correctly'}
        else:
            results['tts'] = {'status': 'error', 'message': 'TTS file not generated'}
    except Exception as e:
        results['tts'] = {'status': 'error', 'message': str(e)}
    
    # STT test requires audio file, skip for now
    results['stt'] = {'status': 'skipped', 'message': 'STT test requires audio file'}
    
    return results
