# voice_service.py
# ĐÂY LÀ MÁY CHỦ AI TỰ HOST DÀNH CHO LUẬN VĂN
# Chạy độc lập tại cổng 5000: python voice_service.py

import os
import uuid
import wave
import json
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
import pyttsx3
from vosk import Model, KaldiRecognizer

app = FastAPI(title="DTHub Local AI Voice Service")

# 1. Cấu hình Model STT (Vosk)
# Tải model từ: https://alphacephei.com/vosk/models
# Giải nén vào thư mục 'models/vosk-model-small-vn'
MODEL_PATH = "models/vosk-model-small-vn"

# Khởi tạo Model STT (Load một lần khi khởi động)
stt_model = None
if os.path.exists(MODEL_PATH):
    print(f"[OK] Đang tải Model STT từ: {MODEL_PATH}")
    stt_model = Model(MODEL_PATH)
else:
    print(f"[!] CẢNH BÁO: Không tìm thấy model tại {MODEL_PATH}. Vui lòng tải về để STT hoạt động.")

# 2. Cấu hình TTS (pyttsx3)
def init_tts_engine():
    engine = pyttsx3.init()
    # Bạn có thể tinh chỉnh giọng đọc mặc định ở đây
    return engine

@app.post("/stt")
async def speech_to_text(audio: UploadFile = File(...), language: str = Form("vi-VN")):
    """Xử lý STT Local bằng Vosk"""
    if not stt_model:
        return JSONResponse({"error": "Model STT chưa được cài đặt"}, status_code=500)
    
    # Lưu file tạm
    temp_wav = f"temp_{uuid.uuid4().hex}.wav"
    with open(temp_wav, "wb") as f:
        f.write(await audio.read())
    
    try:
        wf = wave.open(temp_wav, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            # Nếu file không đúng định dạng (16kHz, Mono, 16-bit), Vosk sẽ lỗi
            # (Bạn nên dùng pydub để convert ở đây nếu cần)
            pass
            
        rec = KaldiRecognizer(stt_model, wf.getframerate())
        text = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                pass
        
        result = json.loads(rec.FinalResult())
        text = result.get("text", "")
        wf.close()
        return {"status": "success", "text": text}
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)

@app.post("/tts")
async def text_to_speech(text: str = Form(...), voice: str = Form("vi"), speed: float = Form(1.0)):
    """Xử lý TTS Local bằng pyttsx3"""
    filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join("media/tts", filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        engine = init_tts_engine()
        # Tìm giọng đọc phù hợp
        voices = engine.getProperty('voices')
        for v in voices:
            if voice in v.languages or voice in v.id.lower():
                engine.setProperty('voice', v.id)
                break
        
        engine.setProperty('rate', int(200 * speed))
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        
        return FileResponse(output_path, media_type="audio/mpeg", filename=filename)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
