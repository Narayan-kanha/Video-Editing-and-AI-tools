# utils/time_utils.py

def ms_to_timestamp(ms: int) -> str:
    """Converts milliseconds to 00:00:00 format"""
    seconds = ms // 1000
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    frames = int((ms % 1000) / 33.3)
    if h > 0:
        return f"{h:02}:{m:02}:{s:02}"
    return f"{m:02}:{s:02}:{frames:02}"

def seconds_to_ass_time(seconds: float) -> str:
    """Converts seconds to ASS format H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"