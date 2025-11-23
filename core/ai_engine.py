# core/ai_engine.py
import whisper
import os
import subprocess

def transcribe_video(video_path: str, model_size: str = "base"):
    """
    Runs Whisper AI.
    Returns: List of subtitle dictionaries or raises Exception.
    """
    try:
        model = whisper.load_model(model_size)
        
        # Fast ffmpeg audio extraction
        temp_audio = "temp_ai.wav"
        command = f'ffmpeg -y -i "{video_path}" -ar 16000 -ac 1 -c:a pcm_s16le "{temp_audio}"'
        subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        result = model.transcribe(temp_audio)
        
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
            
        return result["segments"]
    
    except Exception as e:
        raise e