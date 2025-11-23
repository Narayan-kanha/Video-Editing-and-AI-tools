# core/audio_engine.py
import kanha_core # The Compiled Rust Pyd

def generate_waveform_fast(video_path: str, resolution: int = 1500):
    """Wrapper to call Rust engine safely"""
    try:
        print(f"Sending {video_path} to Rust Core...")
        # The native rust function we wrote
        return kanha_core.get_waveform(video_path, resolution)
    except Exception as e:
        print(f"Rust Waveform Error: {e}")
        return []