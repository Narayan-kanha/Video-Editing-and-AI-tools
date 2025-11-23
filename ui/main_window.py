# ui/main_window.py
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, simpledialog, Menu
import threading
import os
import subprocess
import sys
import numpy as np
import vlc  # type: ignore

# --- Modular Imports ---
from .styles import Theme

# --- DEPENDENCY CHECK ---
try:
    # We only use MoviePy for metadata probing here (duration) to save memory
    from moviepy.editor import VideoFileClip
    import whisper
    DEPENDENCIES_OK = True
except ImportError:
    DEPENDENCIES_OK = False
    print("Warning: AI Libraries missing.")

# --- RUST ENGINE CONNECTION (Your Fix) ---
try:
    # The Senior Developer Fix: Alias the new engine to the old variable name
    import kanha_core as subtitle_engine # type: ignore
    RUST_AVAILABLE = True
    print(">> CORE ENGINE: RUST [ONLINE]")
except ImportError:
    RUST_AVAILABLE = False
    print(">> CORE ENGINE: PYTHON FALLBACK [ONLINE]")

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
        
        # Design State (For Exporting)
        self.font_name = "Arial"
        self.font_size = 60
        self.font_color = "&H00FFFF" # Yellow-ish in BGR default
        self.pos_margin_v = 50

        # --- ENGINE INIT ---
        self.setup_vlc()
        self.create_menu()
        self.create_layout()
        self.start_ui_loop()

    def setup_vlc(self):
        self.vlc_inst = vlc.Instance()
        self.player = self.vlc_inst.media_player_new()

    def create_menu(self):
        menu_bar = Menu(self.root, bg=Theme.BG_MAIN, fg="white", borderwidth=0)
        self.root.config(menu=menu_bar)
        
        file_menu = Menu(menu_bar, tearoff=0, bg="#333", fg="white")
        file_menu.add_command(label="Import Media...", command=self.load_video)
        file_menu.add_separator()
        file_menu.add_command(label="Export Project", command=self.export_project)
        file_menu.add_command(label="Exit", command=self.on_close)
        
        menu_bar.add_cascade(label="File", menu=file_menu)

    def create_layout(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=3)
        self.root.grid_rowconfigure(1, weight=2)

        # --- 1. ASSETS PANEL ---
        self.pnl_assets = ctk.CTkFrame(self.root, fg_color=Theme.BG_PANEL, corner_radius=0)
        self.pnl_assets.grid(row=0, column=0, padx=1, pady=1, sticky="nsew")
        
        self.asset_tabs = ctk.CTkTabview(self.pnl_assets, fg_color=Theme.BG_PANEL)
        self.asset_tabs.pack(fill="both", expand=True, padx=5, pady=5)
        self.asset_tabs.add("Captions")
        self.asset_tabs.add("Project")
        
        # Treeview Styles for "Pro" look
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

        # --- 2. PREVIEW MONITOR ---
        self.pnl_preview = ctk.CTkFrame(self.root, fg_color="black", corner_radius=0)
        self.pnl_preview.grid(row=0, column=1, padx=1, pady=1, sticky="nsew")
        
        self.video_canvas = ctk.CTkCanvas(self.pnl_preview, bg="black", highlightthickness=0)
        self.video_canvas.pack(fill="both", expand=True)
        self.lbl_status = ctk.CTkLabel(self.pnl_preview, text="No Active Sequence", font=Theme.FONT_HEAD, text_color="#555")
        self.lbl_status.place(relx=0.5, rely=0.5, anchor="center")

        # --- 3. TIMELINE ---
        self.pnl_timeline = ctk.CTkFrame(self.root, fg_color=Theme.BG_TIMELINE, corner_radius=0)
        self.pnl_timeline.grid(row=1, column=0, columnspan=2, padx=1, pady=1, sticky="nsew")
        
        # Toolbar
        self.tl_toolbar = ctk.CTkFrame(self.pnl_timeline, height=35, fg_color=Theme.BG_PANEL, corner_radius=0)
        self.tl_toolbar.pack(fill="x", pady=(0,1))
        
        self.time_lbl = ctk.CTkLabel(self.tl_toolbar, text="00:00:00:00", font=("Consolas", 13, "bold"), text_color=Theme.ACCENT_BLUE)
        self.time_lbl.pack(side="left", padx=10)
        
        ctk.CTkButton(self.tl_toolbar, text="▶", width=30, height=25, fg_color="transparent", border_width=1, 
                      border_color="#555", command=self.toggle_play).pack(side="left", padx=5)
        
        ctk.CTkButton(self.tl_toolbar, text="✨ Auto-Caption", width=100, height=25, fg_color=Theme.ACCENT_BLUE, 
                      command=self.run_transcription).pack(side="right", padx=10)

        # Canvas
        self.tl_canvas = ctk.CTkCanvas(self.pnl_timeline, bg=Theme.BG_TIMELINE, highlightthickness=0)
        self.tl_canvas.pack(fill="both", expand=True)
        self.tl_canvas.bind("<Button-1>", self.on_tl_click)
        self.tl_canvas.bind("<B1-Motion>", self.on_tl_drag)
        self.tl_canvas.bind("<Configure>", self.draw_timeline)

    # ------------------------------------------------
    # CORE LOGIC
    # ------------------------------------------------
    def load_video(self):
        path = filedialog.askopenfilename()
        if not path: return
        self.video_path = path
        self.lbl_status.place_forget()
        
        m = self.vlc_inst.media_new(path)
        self.player.set_media(m)
        self.player.set_hwnd(self.video_canvas.winfo_id())
        self.player.play()
        self.root.after(100, self.player.pause)
        
        # Quick Duration Check
        try:
            import json
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", self.video_path]
            out = subprocess.check_output(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0).decode()
            data = json.loads(out)
            self.duration = float(data["streams"][0]["duration"])
        except:
            self.duration = 60.0
            
        threading.Thread(target=self.analyze_waveform, daemon=True).start()

    def analyze_waveform(self):
        if RUST_AVAILABLE:
            try:
                print("RUST ENGINE: High-Speed Analysis...")
                self.waveform_points = subtitle_engine.get_waveform(self.video_path, 2000)
            except Exception as e: 
                print(f"Rust Error: {e}")
                self.fallback_waveform()
        else:
            self.fallback_waveform()
        self.root.after(0, self.draw_timeline)

    def fallback_waveform(self):
        print("Using randomized waveform fallback.")
        self.waveform_points = list(np.random.rand(2000) * 0.6)

    def toggle_play(self):
        if self.player.is_playing(): self.player.pause()
        else: self.player.play()

    # ------------------------------------------------
    # AI LOGIC
    # ------------------------------------------------
    def run_transcription(self):
        if not self.video_path: return
        self.lbl_status.configure(text="AI Analyzing...", text_color=Theme.ACCENT_BLUE)
        self.lbl_status.place(relx=0.5, rely=0.5)
        threading.Thread(target=self._transcribe_worker, daemon=True).start()

    def _transcribe_worker(self):
        try:
            # Extract Audio directly
            cmd = f'ffmpeg -y -i "{self.video_path}" -ar 16000 -ac 1 -c:a pcm_s16le temp_sys.wav'
            subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            
            model = whisper.load_model(self.ai_model.get())
            res = model.transcribe("temp_sys.wav")
            self.subtitle_segments = res["segments"]
            
            try: os.remove("temp_sys.wav") 
            except: pass
            
            self.root.after(0, self._ai_done)
        except Exception as e:
            print(e)

    def _ai_done(self):
        self.lbl_status.place_forget()
        self.asset_tabs.set("Captions")
        for i in self.caption_tree.get_children(): self.caption_tree.delete(i)
        for i, s in enumerate(self.subtitle_segments):
            self.caption_tree.insert("", "end", iid=str(i), values=(f"{s['start']:.1f}s", s['text']))
        self.draw_timeline()

    def edit_caption(self, event):
        item = self.caption_tree.selection()
        if not item: return
        idx = int(item[0])
        current = self.subtitle_segments[idx]
        
        # Jump video
        self.player.set_time(int(current['start'] * 1000))
        
        new = simpledialog.askstring("Edit", "Content:", initialvalue=current['text'])
        if new:
            self.subtitle_segments[idx]['text'] = new
            self.caption_tree.item(item, values=(f"{current['start']:.1f}s", new))
            self.draw_timeline()

    # ------------------------------------------------
    # RENDER ENGINE (The "Hard Core" Mode)
    # ------------------------------------------------
    def export_project(self):
        if not self.video_path: return
        out = filedialog.asksaveasfilename(defaultextension=".mp4")
        if not out: return
        
        threading.Thread(target=self._render_worker, args=(out,), daemon=True).start()

    def _render_worker(self, out_path):
        try:
            ass_path = "temp_render.ass"
            
            # Generate .ass Script
            script = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, Alignment, MarginV
Style: Default,{self.font_name},{self.font_size},{self.font_color},2,{self.pos_margin_v}
[Events]
Format: Layer, Start, End, Style, Text
"""
            with open(ass_path, "w", encoding="utf-8") as f:
                f.write(script)
                for s in self.subtitle_segments:
                    # Convert seconds to H:MM:SS.cs
                    def fmt(t):
                        h, m = divmod(t, 3600)
                        m, s = divmod(m, 60)
                        cs = int((s - int(s)) * 100)
                        return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"
                    
                    start = fmt(s['start'])
                    end = fmt(s['end'])
                    text = s['text'].replace("\n", "\\N")
                    f.write(f"Dialogue: 0,{start},{end},Default,{text}\n")

            # Execute C++ Render
            clean_sub = ass_path.replace("\\", "/").replace(":", "\\\\:")
            cmd = [
                "ffmpeg", "-y", 
                "-i", self.video_path,
                "-vf", f"subtitles='{clean_sub}'",
                "-c:v", "libx264", "-c:a", "copy",
                "-preset", "fast", out_path
            ]
            
            subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            os.remove(ass_path)
            
            messagebox.showinfo("Success", "Render Complete!")
            
        except Exception as e:
            print(f"Export Error: {e}")

    # ------------------------------------------------
    # VISUALS (TIMELINE)
    # ------------------------------------------------
    def draw_timeline(self, event=None):
        self.tl_canvas.delete("all")
        w = self.tl_canvas.winfo_width()
        h = self.tl_canvas.winfo_height()
        track_h = 60
        
        # -- TRACK V1 --
        self.draw_track(10, w, track_h, "V1", Theme.TRACK_VID_BG)
        # Draw Blue Waveform (Native Rust Data)
        if self.waveform_points:
            mid = 10 + (track_h/2)
            bar = w / len(self.waveform_points)
            pts = []
            for i, val in enumerate(self.waveform_points):
                pts.extend([i*bar, mid-(val*25)])
            for i, val in reversed(list(enumerate(self.waveform_points))):
                pts.extend([i*bar, mid+(val*25)])
            self.tl_canvas.create_polygon(pts, fill=Theme.TRACK_VID_FG, outline="")

        # -- TRACK S1 (SUBS) --
        self.draw_track(10 + track_h + 5, w, track_h, "S1", Theme.TRACK_SUB_BG)
        if self.subtitle_segments and self.duration > 0:
            px = w / self.duration
            y_pos = 10 + track_h + 5
            for s in self.subtitle_segments:
                sx, ex = s['start'] * px, s['end'] * px
                if ex-sx < 3: ex = sx + 3
                self.tl_canvas.create_rectangle(sx, y_pos+10, ex, y_pos+track_h-10, 
                                              fill=Theme.TRACK_SUB_FG, outline="#000")
                if ex-sx > 20:
                    self.tl_canvas.create_text(sx+5, y_pos+30, text=s['text'][:15], anchor="w", fill="white", font=("Arial",8))

        # -- PLAYHEAD --
        if self.duration > 0:
            x = (self.player.get_time()/1000 / self.duration) * w
            self.tl_canvas.create_line(x,0,x,h, fill=Theme.RED_PLAYHEAD, width=2)

    def draw_track(self, y, w, h, title, bg):
        self.tl_canvas.create_rectangle(0, y, 60, y+h, fill="#333", outline="") # Header
        self.tl_canvas.create_text(30, y+h/2, text=title, fill="gray", font=("Arial", 9, "bold"))
        self.tl_canvas.create_rectangle(60, y, w, y+h, fill="#1a1a1a", outline="#333") # Bed

    def on_tl_click(self, e):
        if e.x > 60 and self.duration > 0:
            w = self.tl_canvas.winfo_width() - 60
            t = ((e.x - 60) / w) * self.duration
            self.player.set_time(int(t*1000))
            self.draw_timeline()

    def on_tl_drag(self, e): self.on_tl_click(e)

    def start_ui_loop(self):
        if self.player.is_playing():
            t = self.player.get_time()
            if t>=0: 
                self.redraw_ui(t)
        self.root.after(40, self.start_ui_loop)

    def redraw_ui(self, t_ms):
        sec = t_ms // 1000
        self.time_lbl.configure(text=f"{sec//3600:02}:{(sec%3600)//60:02}:{sec%60:02}")
        self.draw_timeline()

    def on_close(self):
        self.player.stop()
        self.root.destroy()
        os._exit(0)