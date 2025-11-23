# ui/styles.py

class Theme:
    # Adobe Dark Interface
    BG_MAIN = "#1d1d1d"       # Main Window Background
    BG_PANEL = "#2a2a2a"      # Individual Panel Backgrounds
    BG_TIMELINE = "#181818"   # Timeline Deep Background
    
    # Accents
    ACCENT_BLUE = "#3997f3"   # Premiere selection blue
    TEXT_WHITE = "#dddddd"    # Soft white text
    TEXT_GRAY = "#999999"     # Metadata text
    
    # Tracks (Specific Adobe Shades)
    TRACK_HEADER = "#333333"  # The box that says "V1"
    CLIP_VIDEO = "#6d839b"    # Pale Blue for Video
    CLIP_AUDIO = "#3e5f3e"    # Green for Audio (Adobe Audition style)
    CLIP_SUBTITLE = "#b78029" # Gold/Orange for text/graphics
    
    RED_PLAYHEAD = "#cd3232"
    
    # Borders/Seams
    BORDER_COLOR = "#111111"
    
    # Fonts (Adobe uses condensed fonts usually)
    FONT_MAIN = ("Segoe UI", 11)
    FONT_HEAD = ("Segoe UI", 12, "bold")
    FONT_SMALL = ("Consolas", 9)