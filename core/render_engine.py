# core/render_engine.py
import subprocess
import os
import sys
from utils.time_utils import seconds_to_ass_time

def generate_ass_file(segments, font_settings, path="temp_subtitles.ass"):
    # Construct .ass file logic (copied from your previous code)
    # Simplified here for brevity of the plan
    hex_color = font_settings['color'].lstrip('#')
    bgr_color = f"&H00{hex_color[4:6]}{hex_color[2:4]}{hex_color[0:2]}"
    
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, Outline, Shadow, Alignment, MarginV, Encoding
Style: Default,{font_settings['font']},{font_settings['size']},{bgr_color},2,0,2,{font_settings['y_pos']},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for s in segments:
            start = seconds_to_ass_time(s['start'])
            end = seconds_to_ass_time(s['end'])
            text = s['text'].replace("\n", "\\N")
            f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")
    return path

def export_video_with_ffmpeg(video_path, ass_path, output_path):
    """
    Calls the system FFmpeg to burn subtitles via .ass file
    """
    sub_arg = ass_path.replace("\\", "/").replace(":", "\\\\:")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles='{sub_arg}'",
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "copy",
        output_path
    ]
    
    # Windows process handling to hide console
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                               startupinfo=startupinfo, universal_newlines=True)
    return process