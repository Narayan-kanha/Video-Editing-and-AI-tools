# ui/main_window.py
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, simpledialog, Menu
import threading
import os
import subprocess
import numpy as np
import vlc #type: ignore

# Import Modular Assets
from .styles import Theme

# --- TRY LOADING DEPENDENCIES ---
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
    import whisper
    DEPENDENCIES_OK = True
except ImportError:
    DEPENDENCIES_OK = False
    print("Warning: MoviePy or Whisper not found. AI functions disabled.")

# --- TRY RUST ---
try:
    import kanha_core as subtitle_engine #type: ignore
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.configure(fg_color=Theme.BG_MAIN)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # --- STATE ---
        self.video_path = None
        self.duration = 0.0
        self.is_playing = False
        self.waveform_points = []
        self.subtitle_segments = []
        self.ai_model = ctk.StringVar(value="base")
        
        # --- INIT ENGINE ---
        self.setup_vlc()
        self.create_menu()
        self.create_layout()
        self.start_ui_loop()

    def setup_vlc(self):
        self.vlc_inst = vlc.Instance()
        self.player = self.vlc_inst.media_player_new()

    def create_menu(self):
        # Premiere Style Top Menu
        menu_bar = Menu(self.root, bg=Theme.BG_MAIN, fg=Theme.TEXT_WHITE, borderwidth=0)
        self.root.config(menu=menu_bar)
        
        file_menu = Menu(menu_bar, tearoff=0, bg="#333", fg="white")
        file_menu.add_command(label="Import Media...", command=self.load_video)
        file_menu.add_separator()
        file_menu.add_command(label="Export Media (Ctrl+M)", command=self.export_project)
        file_menu.add_command(label="Exit", command=self.on_close)
        
        seq_menu = Menu(menu_bar, tearoff=0, bg="#333", fg="white")
        seq_menu.add_command(label="Auto-Caption Sequence", command=self.run_transcription)
        
        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="Sequence", menu=seq_menu)

    def create_layout(self):
        # Main Container - Darker Borders
        # Configure grid to look like panels
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1) # Preview takes equal or more
        self.root.grid_rowconfigure(0, weight=3) # Top Panel height
        self.root.grid_rowconfigure(1, weight=2) # Timeline height

        # --- 1. SOURCE/ASSETS PANEL (Top Left) ---
        self.pnl_assets = ctk.CTkFrame(self.root, fg_color=Theme.BG_PANEL, corner_radius=0)
        self.pnl_assets.grid(row=0, column=0, padx=1, pady=1, sticky="nsew")
        
        self.asset_tabs = ctk.CTkTabview(self.pnl_assets, fg_color=Theme.BG_PANEL, 
                                         segmented_button_fg_color=Theme.BG_TIMELINE,
                                         text_color="#aaa")
        self.asset_tabs.pack(fill="both", expand=True, padx=5, pady=5)
        self.asset_tabs.add("Project")
        self.asset_tabs.add("Captions")
        
        # Custom Styled Treeview
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#222", foreground="#ddd", fieldbackground="#222", borderwidth=0)
        style.configure("Treeview.Heading", background="#333", foreground="#eee", relief="flat")
        style.map("Treeview", background=[('selected', Theme.ACCENT_BLUE)])
        
        self.caption_tree = ttk.Treeview(self.asset_tabs.tab("Captions"), columns=("start", "text"), show="headings")
        self.caption_tree.heading("start", text="Time")
        self.caption_tree.column("start", width=60)
        self.caption_tree.heading("text", text="Content")
        self.caption_tree.pack(fill="both", expand=True)
        self.caption_tree.bind("<Double-1>", self.edit_caption)

        # --- 2. PROGRAM MONITOR (Top Right) ---
        self.pnl_preview = ctk.CTkFrame(self.root, fg_color="black", corner_radius=0)
        self.pnl_preview.grid(row=0, column=1, padx=1, pady=1, sticky="nsew")
        
        self.video_canvas = ctk.CTkCanvas(self.pnl_preview, bg="black", highlightthickness=0)
        self.video_canvas.pack(fill="both", expand=True)
        self.lbl_status = ctk.CTkLabel(self.pnl_preview, text="No Sequence Active", font=Theme.FONT_HEAD, text_color="#555")
        self.lbl_status.place(relx=0.5, rely=0.5, anchor="center")

        # --- 3. TIMELINE (Bottom Full Width) ---
        self.pnl_timeline = ctk.CTkFrame(self.root, fg_color=Theme.BG_TIMELINE, corner_radius=0)
        self.pnl_timeline.grid(row=1, column=0, columnspan=2, padx=1, pady=1, sticky="nsew")
        
        # Toolbar
        self.tl_toolbar = ctk.CTkFrame(self.pnl_timeline, height=35, fg_color=Theme.BG_PANEL, corner_radius=0)
        self.tl_toolbar.pack(fill="x", pady=(0,1))
        
        self.time_lbl = ctk.CTkLabel(self.tl_toolbar, text="00:00:00:00", font=("Consolas", 13, "bold"), text_color=Theme.ACCENT_BLUE)
        self.time_lbl.pack(side="left", padx=10)
        
        ctk.CTkButton(self.tl_toolbar, text="▶", width=30, height=25, fg_color="transparent", border_width=1, 
                      border_color="#555", command=self.toggle_play).pack(side="left", padx=5)

        # Tracks Area
        self.tl_canvas = ctk.CTkCanvas(self.pnl_timeline, bg=Theme.BG_TIMELINE, highlightthickness=0)
        self.tl_canvas.pack(fill="both", expand=True)
        self.tl_canvas.bind("<Button-1>", self.on_tl_click)
        self.tl_canvas.bind("<B1-Motion>", self.on_tl_drag)
        self.tl_canvas.bind("<Configure>", self.draw_timeline)

    # ------------------------------------------------
    # CORE ENGINE LOGIC (RESTORED)
    # ------------------------------------------------
    def load_video(self):
        path = filedialog.askopenfilename()
        if not path: return
        self.video_path = path
        self.lbl_status.place_forget()
        
        # VLC Init
        m = self.vlc_inst.media_new(path)
        self.player.set_media(m)
        self.player.set_hwnd(self.video_canvas.winfo_id())
        self.player.play()
        self.root.after(200, self.player.pause)
        
        # Async Analysis
        threading.Thread(target=self.analyze_media, daemon=True).start()

    def analyze_media(self):
        # Duration
        try:
            import json
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", self.video_path]
            out = subprocess.check_output(cmd).decode()
            data = json.loads(out)
            dur_str = data["streams"][0]["duration"]
            self.duration = float(dur_str)
        except:
            self.duration = 60.0 # Fallback
            
        # Waveform
        if RUST_AVAILABLE:
            try:
                print("RUST ENGINE: Analyzing Waveform...")
                self.waveform_points = subtitle_engine.generate_waveform(self.video_path, 2000)
            except: self.fallback_waveform()
        else:
            self.fallback_waveform()
            
        self.root.after(0, self.draw_timeline)

    def fallback_waveform(self):
        # Pure python random noise approximation just for visuals
        self.waveform_points = list(np.random.rand(1000) * 0.5)

    def run_transcription(self):
        if not self.video_path or not DEPENDENCIES_OK: 
            messagebox.showerror("Error", "AI Modules missing or No Video Loaded")
            return
        
        self.lbl_status.configure(text="Analyzing Audio...", text_color=Theme.ACCENT_BLUE)
        self.lbl_status.place(relx=0.5, rely=0.5)
        threading.Thread(target=self._transcribe_task, daemon=True).start()

    def _transcribe_task(self):
        try:
            # Extract Audio with FFmpeg (Fastest)
            subprocess.run(f'ffmpeg -y -i "{self.video_path}" -ar 16000 -ac 1 -c:a pcm_s16le temp_ai.wav', 
                           shell=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            
            model = whisper.load_model(self.ai_model.get())
            res = model.transcribe("temp_ai.wav")
            self.subtitle_segments = res["segments"]
            try: os.remove("temp_ai.wav") 
            except: pass
            
            self.root.after(0, self.populate_captions)
        except Exception as e:
            print(e)

    def populate_captions(self):
        self.lbl_status.place_forget()
        self.asset_tabs.set("Captions")
        for i in self.caption_tree.get_children(): self.caption_tree.delete(i)
        for i, s in enumerate(self.subtitle_segments):
            self.caption_tree.insert("", "end", iid=str(i), values=(f"{s['start']:.1f}s", s['text']))
        self.draw_timeline()

    # ------------------------------------------------
    # TIMELINE DRAWING (PREMIERE PRO STYLE)
    # ------------------------------------------------
    def draw_timeline(self, event=None):
        self.tl_canvas.delete("all")
        w = self.tl_canvas.winfo_width()
        h = self.tl_canvas.winfo_height()
        
        # Config
        track_h = 60
        gutter = 20 # Space on left for headers
        
        # --- V1 TRACK (VIDEO) ---
        y_v1 = 20
        # Header
        self.tl_canvas.create_rectangle(0, y_v1, gutter+30, y_v1+track_h, fill=Theme.TRACK_HEADER, outline="")
        self.tl_canvas.create_text(25, y_v1+30, text="V1", fill="#aaa", font=("Arial", 10, "bold"))
        
        # Track Bed
        self.tl_canvas.create_rectangle(gutter+30, y_v1, w, y_v1+track_h, fill="#151515", outline=Theme.BG_PANEL)
        
        # Clip Content (Waveform)
        if self.waveform_points:
            track_w = w - (gutter+30)
            bar_w = track_w / len(self.waveform_points)
            mid = y_v1 + (track_h/2)
            # We mimic Premiere's half-waveform look sometimes, or full mirrored
            # Simple Polygon
            pts = []
            for i, val in enumerate(self.waveform_points):
                pts.extend([gutter+30 + i*bar_w, mid - (val*25)])
            for i, val in reversed(list(enumerate(self.waveform_points))):
                pts.extend([gutter+30 + i*bar_w, mid + (val*25)])
            
            # Blue clip bg
            self.tl_canvas.create_rectangle(gutter+30, y_v1, w, y_v1+track_h, fill="#22303f", outline=Theme.ACCENT_BLUE, width=1)
            self.tl_canvas.create_polygon(pts, fill=Theme.TRACK_VID_FG, outline="")

        # --- A1 TRACK (SUBTITLES SIMULATED) ---
        y_sub = y_v1 + track_h + 5
        
        # Header
        self.tl_canvas.create_rectangle(0, y_sub, gutter+30, y_sub+track_h, fill=Theme.TRACK_HEADER, outline="")
        self.tl_canvas.create_text(25, y_sub+30, text="S1", fill="#aaa", font=("Arial", 10, "bold"))
        # Bed
        self.tl_canvas.create_rectangle(gutter+30, y_sub, w, y_sub+track_h, fill="#151515", outline=Theme.BG_PANEL)

        if self.subtitle_segments and self.duration > 0:
            track_w = w - (gutter+30)
            px_sec = track_w / self.duration
            
            for s in self.subtitle_segments:
                sx = (gutter+30) + (s['start'] * px_sec)
                ex = (gutter+30) + (s['end'] * px_sec)
                if ex-sx < 2: ex = sx + 2
                
                # Premiere "Pink/Orange" graphic clip style
                self.tl_canvas.create_rectangle(sx, y_sub+5, ex, y_sub+track_h-5, 
                                              fill=Theme.CLIP_SUBTITLE, outline="#7d571c")
                
                if ex-sx > 30:
                    self.tl_canvas.create_text(sx+5, y_sub+30, text=s['text'], anchor="w", font=Theme.FONT_SMALL, fill="white")

        # --- TIME RULER & PLAYHEAD ---
        # Draw top ruler
        self.tl_canvas.create_rectangle(gutter+30, 0, w, 20, fill="#222", outline="")
        
        # Playhead
        if self.duration > 0:
            t = self.player.get_time() / 1000
            track_w = w - (gutter+30)
            px = (gutter+30) + (t / self.duration * track_w)
            
            self.tl_canvas.create_line(px, 0, px, h, fill=Theme.RED_PLAYHEAD, width=1)
            self.tl_canvas.create_polygon(px-5, 0, px+5, 0, px, 15, fill=Theme.RED_PLAYHEAD)

    # ------------------------------------------------
    # CONTROLS
    # ------------------------------------------------
    def toggle_play(self):
        if self.player.is_playing(): self.player.pause()
        else: self.player.play()

    def on_tl_click(self, event):
        # Check if click is in track area
        if event.x > 50 and self.duration > 0:
            w = self.tl_canvas.winfo_width() - 50
            pct = (event.x - 50) / w
            self.player.set_time(int(pct * self.duration * 1000))
            self.draw_timeline()

    def on_tl_drag(self, event):
        self.on_tl_click(event)

    def edit_caption(self, event):
        item = self.caption_tree.selection()
        if not item: return
        idx = int(item[0])
        txt = self.subtitle_segments[idx]['text']
        
        new = simpledialog.askstring("Editor", "Caption Text:", initialvalue=txt)
        if new:
            self.subtitle_segments[idx]['text'] = new
            self.populate_captions()

    def export_project(self):
        messagebox.showinfo("Export", "Renderer ready to link to FFmpeg/C++ engine.")

    def start_ui_loop(self):
        if self.player.is_playing():
            self.draw_timeline()
            t = self.player.get_time()
            self.time_lbl.configure(text=self.ms_to_timecode(t))
        self.root.after(40, self.start_ui_loop)

    def ms_to_timecode(self, ms):
        s, ms = divmod(max(0, ms), 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        frames = int(ms / 33) 
        return f"{h:02}:{m:02}:{s:02}:{frames:02}"

    def on_close(self):
        self.player.stop()
        self.root.destroy()
        os._exit(0)