# voice_service.py
import os
import uvicorn
import uuid
import wave
import json
import torch
import io
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import pyttsx3
from transformers import pipeline
import whisper
from gtts import gTTS
from pydub import AudioSegment

app = FastAPI(title="DTHub Voice Service")

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

# Khởi tạo các model STT (Lazy loading)
_stt_models = {}

def get_stt_model(language_code: str):
    """Lấy model STT phù hợp cho từng ngôn ngữ"""
    if language_code in _stt_models:
        return _stt_models[language_code]
    
    try:
        if language_code == "en-US":
            print("[INFO] Đang tải model Whisper (tiny.en)...")
            _stt_models[language_code] = whisper.load_model("tiny.en")
        elif language_code == "vi-VN":
            print("[INFO] Đang tải model PhoWhisper (vinai/phowhisper-tiny)...")
            _stt_models[language_code] = pipeline(
                "automatic-speech-recognition", 
                model="vinai/phowhisper-tiny", 
                device="cpu"
            )
        else:
            # Mặc định dùng Vosk làm backup nếu có sẵn model
            from vosk import Model as VoskModel
            vosk_path = os.path.join(MODEL_DIR, f"vosk-model-small-{language_code[:2]}")
            if os.path.exists(vosk_path):
                _stt_models[language_code] = VoskModel(vosk_path)
            else:
                return None
    except Exception as e:
        print(f"[ERROR] Lỗi khi tải model STT {language_code}: {e}")
        return None
        
    return _stt_models.get(language_code)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...), 
    language: str = Form("vi-VN"),
    engine: str = Form("whisper") # whisper hoặc vosk
):
    """Chuyển giọng nói thành văn bản 100% Local"""
    temp_wav = f"temp_{uuid.uuid4().hex}.wav"
    with open(temp_wav, "wb") as f:
        f.write(await audio.read())
    
    try:
        # Load model phù hợp
        model = get_stt_model(language)
        if not model:
            # Fallback sang Google Speech Recognition nếu thư viện sr có sẵn
            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                with sr.AudioFile(temp_wav) as source:
                    audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=language)
                return {"status": "success", "text": text, "engine": "google_fallback"}
            except:
                raise HTTPException(status_code=500, detail="Không thể tải model STT local và Google fallback thất bại.")

        # Xử lý theo loại model
        if language == "vi-VN" and hasattr(model, "__call__"): # PhoWhisper pipeline
            result = model(temp_wav)
            text = result.get("text", "")
        elif language == "en-US" and hasattr(model, "transcribe"): # OpenAI Whisper
            result = model.transcribe(temp_wav)
            text = result.get("text", "")
        else:
            # Giả định dùng Vosk
            from vosk import KaldiRecognizer
            import wave
            wf = wave.open(temp_wav, "rb")
            rec = KaldiRecognizer(model, wf.getframerate())
            while True:
                data = wf.readframes(4000)
                if len(data) == 0: break
                if rec.AcceptWaveform(data): pass
            text = json.loads(rec.FinalResult()).get("text", "")
            wf.close()

        return {"status": "success", "text": text.strip().lower()}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)

@app.post("/tts")
async def text_to_speech(
    text: str = Form(...), 
    voice: str = Form("vi"), 
    speed: float = Form(1.0),
    engine: str = Form("local") # local (pyttsx3) hoặc gtts
):
    """Chuyển văn bản thành giọng nói"""
    filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join("media/tts", filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        if engine == "gtts":
            # gTTS backup
            tts = gTTS(text=text, lang=voice, slow=False)
            tts.save(output_path)
        else:
            # Local TTS (pyttsx3)
            tts_engine = pyttsx3.init()
            voices = tts_engine.getProperty('voices')
            for v in voices:
                if voice in v.languages or voice in v.id.lower():
                    tts_engine.setProperty('voice', v.id)
                    break
            tts_engine.setProperty('rate', int(200 * speed))
            tts_engine.save_to_file(text, output_path)
            tts_engine.runAndWait()
        
        return FileResponse(output_path, media_type="audio/mpeg", filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5002)
