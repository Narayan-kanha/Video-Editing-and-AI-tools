# ui/main_window.py
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, Menu
import os
import threading
import vlc 
# Core Imports
from .styles import Theme
# Import the rust-accelerated logic if possible, or python fallback
try:
    from core.audio_engine import generate_waveform_fast
except ImportError:
    # Temporary fallback inside UI if core isn't set up perfect yet
    def generate_waveform_fast(path, res): return []

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # --- State ---
        self.video_path = None
        self.is_playing = False
        self.duration = 0.0
        self.waveform_data = []
        
        # --- Components ---
        self.setup_vlc()
        self.create_menu()
        self.create_layout()
        self.start_update_loop()

    def setup_vlc(self):
        self.vlc_inst = vlc.Instance()
        self.player = self.vlc_inst.media_player_new()

    def create_menu(self):
        menu_bar = Menu(self.root)
        self.root.config(menu=menu_bar)
        
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Import Media", command=self.load_video)
        file_menu.add_command(label="Exit", command=self.on_close)
        menu_bar.add_cascade(label="File", menu=file_menu)

    def create_layout(self):
        # Use PanedWindow for Professional Resizing
        self.main_pane = ttk.PanedWindow(self.root, orient="horizontal")
        self.main_pane.pack(fill="both", expand=True)
        
        # --- LEFT SIDE (Timeline + Preview) ---
        self.left_pane = ttk.PanedWindow(self.main_pane, orient="vertical")
        self.main_pane.add(self.left_pane, weight=3)
        
        # 1. Preview Area
        self.preview_frame = ctk.CTkFrame(self.left_pane, fg_color="black")
        self.left_pane.add(self.preview_frame, weight=3)
        
        self.video_canvas = ctk.CTkCanvas(self.preview_frame, bg="black", highlightthickness=0)
        self.video_canvas.pack(fill="both", expand=True)
        self.lbl_overlay = ctk.CTkLabel(self.preview_frame, text="Load Video", font=Theme.FONT_HEAD)
        self.lbl_overlay.place(relx=0.5, rely=0.5, anchor="center")

        # 2. Timeline Area
        self.timeline_frame = ctk.CTkFrame(self.left_pane, fg_color=Theme.BG_TIMELINE)
        self.left_pane.add(self.timeline_frame, weight=2)
        
        # Timeline Controls (Toolbar)
        self.controls = ctk.CTkFrame(self.timeline_frame, height=40, fg_color=Theme.BG_PANEL)
        self.controls.pack(fill="x")
        
        self.btn_play = ctk.CTkButton(self.controls, text="▶", width=40, command=self.toggle_play)
        self.btn_play.pack(side="left", padx=5, pady=5)
        
        self.time_lbl = ctk.CTkLabel(self.controls, text="00:00:00", font=("Consolas", 12))
        self.time_lbl.pack(side="left", padx=10)

        # Timeline Canvas
        self.tl_canvas = ctk.CTkCanvas(self.timeline_frame, bg=Theme.BG_TIMELINE, highlightthickness=0)
        self.tl_canvas.pack(fill="both", expand=True)
        self.tl_canvas.bind("<Button-1>", self.tl_click)
        self.tl_canvas.bind("<B1-Motion>", self.tl_drag)
        self.tl_canvas.bind("<Configure>", self.redraw_timeline)

        # --- RIGHT SIDE (Inspector / Assets) ---
        self.right_pane = ctk.CTkFrame(self.main_pane, fg_color=Theme.BG_PANEL)
        self.main_pane.add(self.right_pane, weight=1)
        
        self.tabview = ctk.CTkTabview(self.right_pane)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        self.tabview.add("Properties")
        self.tabview.add("Captions")

    # --- LOGIC ---
    def load_video(self):
        path = filedialog.askopenfilename()
        if not path: return
        self.video_path = path
        self.lbl_overlay.place_forget()
        
        # VLC Load
        media = self.vlc_inst.media_new(path)
        self.player.set_media(media)
        self.player.set_hwnd(self.video_canvas.winfo_id())
        self.player.play()
        self.root.after(100, self.player.pause)
        
        # Set stub duration (Rust waveform will handle data)
        self.duration = 60.0 
        
        # Start Rust Waveform Generation
        threading.Thread(target=self.run_waveform_analysis, daemon=True).start()

    def run_waveform_analysis(self):
        # Uses your new Rust Engine via the Python Wrapper
        # Resolving resolution based on canvas width usually happens on draw
        # For calculation, we ask for a fixed high res array
        if self.video_path:
            self.waveform_data = generate_waveform_fast(self.video_path, 1500)
            self.root.after(0, self.redraw_timeline)

    def toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
            self.btn_play.configure(text="▶")
            self.is_playing = False
        else:
            self.player.play()
            self.btn_play.configure(text="⏸")
            self.is_playing = True

    def tl_click(self, event):
        if self.duration <= 0: return
        w = self.tl_canvas.winfo_width()
        t = (event.x / w) * self.duration
        self.player.set_time(int(t * 1000))
        self.redraw_timeline()

    def tl_drag(self, event):
        self.tl_click(event)

    def redraw_timeline(self, event=None):
        self.tl_canvas.delete("all")
        w = self.tl_canvas.winfo_width()
        h = self.tl_canvas.winfo_height()
        
        # 1. Waveform
        if self.waveform_data:
            mid = h / 2
            bar_w = w / len(self.waveform_data)
            points = []
            # Top
            for i, val in enumerate(self.waveform_data):
                points.extend([i*bar_w, mid - (val*50)])
            # Bottom
            for i, val in reversed(list(enumerate(self.waveform_data))):
                points.extend([i*bar_w, mid + (val*50)])
                
            self.tl_canvas.create_polygon(points, fill=Theme.TRACK_VID_FG, outline="")

        # 2. Playhead
        if self.player:
            t_ms = self.player.get_time()
            if t_ms >= 0 and self.duration > 0:
                x = (t_ms / 1000 / self.duration) * w
                self.tl_canvas.create_line(x, 0, x, h, fill=Theme.RED_PLAYHEAD, width=2)

    def start_update_loop(self):
        if self.is_playing:
            t = self.player.get_time()
            if t >= 0:
                sec = t // 1000
                self.time_lbl.configure(text=f"{sec//60:02}:{sec%60:02}")
                self.redraw_timeline()
        self.root.after(30, self.start_update_loop)

    def on_close(self):
        self.player.stop()
        self.root.destroy()
        os._exit(0)