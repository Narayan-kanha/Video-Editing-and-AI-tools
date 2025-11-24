import threading
import time

class AIEngine:
    """ 
    Handles background AI tasks (Captioning, Object Removal).
    Actual implementation will use libraries like 'faster-whisper' or 'stable-diffusion' later.
    """
    
    def __init__(self):
        self.is_busy = False

    def auto_caption(self, audio_path, on_complete_callback):
        """ Runs transcription in a background thread """
        if self.is_busy: return False
        
        self.is_busy = True
        t = threading.Thread(target=self._run_captioning, args=(audio_path, on_complete_callback))
        t.start()
        return True

    def _run_captioning(self, audio_path, callback):
        print(f"🤖 AI: Starting transcription for {audio_path}")
        # --- STUB: SIMULATE AI WORK ---
        time.sleep(2) 
        # In future, put OpenAI/Whisper code here
        result = [
            {"start": 0.5, "end": 2.0, "text": "Hello world"},
            {"start": 2.2, "end": 4.0, "text": "Welcome to Kanha Studio"}
        ]
        # ------------------------------
        print("🤖 AI: Transcription Complete")
        self.is_busy = False
        callback(result)