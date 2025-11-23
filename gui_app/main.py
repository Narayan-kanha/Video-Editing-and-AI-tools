import customtkinter as ctk
from tkinter import filedialog, ttk, simpledialog, messagebox, Menu
import threading
import os
import time
import math
import numpy as np
import subprocess

# ==========================================
# 1. DEPENDENCY MANAGEMENT
# ==========================================
try:
    # Critical Libraries for NLE
    import vlc
    import whisper
    from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
except ImportError as e:
    print("\n---------------------------------------------------")
    print("CRITICAL ERROR: MISSING LIBRARIES")
    print(f"System Report: {e}")
    print("Please run: pip install customtkinter moviepy==1.0.3 openai-whisper python-vlc numpy pillow")
    print("---------------------------------------------------\n")

# Plugin Import: Rust Interop (Optional High-Speed Backend)
RUST_AVAILABLE = False
try:
    import subtitle_engine
    RUST_AVAILABLE = True
    print(">> CORE ENGINE: RUST ACCELERATION [ONLINE]")
except ImportError:
    print(">> CORE ENGINE: PYTHON FALLBACK [ONLINE]")

# ==========================================
# 2. GLOBAL STYLING & CONFIG
# ==========================================
class OpenShotStyleConfig:
    """ Deep Dark 'Pro' Application Theme """
    BG_MAIN = "#1b1b1b"       
    BG_PANEL = "#252525"      
    BG_TIMELINE = "#121212"   
    
    # Industry Standard Track Colors
    TRACK_VID_BG = "#1f2a36"
    TRACK_VID_FG = "#4a90e2" # Vibrant Blue Waveform
    TRACK_SUB_BG = "#3e2723"
    TRACK_SUB_FG = "#ff9800" # High Contrast Orange
    
    ACCENT_BLUE = "#2196f3"
    RED_PLAYHEAD = "#ff5252"
    TEXT_WHITE = "#e0e0e0"
    TEXT_GRAY = "#888888"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ==========================================
# 3. THE APPLICATION ENGINE
# ==========================================
class OpenShotEditorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Kanha AI Studio - NLE Professional")
        self.geometry("1600x900")
        self.configure(fg_color=OpenShotStyleConfig.BG_MAIN)
        
        # Prevent instant crash on close if threads are running
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- State & Data ---
        self.video_path = None
        self.duration = 0
        self.is_playing = False
        self.is_exporting = False
        self.waveform_points = []
        self.subtitle_segments = [] # List[Dict]: {'start', 'end', 'text'}
        self.ai_model = ctk.StringVar(value="base") # whisper model size

        # --- Engine Initialization ---
        self.vlc_instance = vlc.Instance()
        self.media_player = self.vlc_instance.media_player_new()

        # --- Build the Interface ---
        self.create_menu_bar()
        self.create_layout()

        # --- Event Bindings ---
        self.bind("<Configure>", self.on_window_resize)
        
        # --- Start Heartbeat Loop ---
        self.update_ui_loop()

    # ------------------------------------------------------
    # GUI CONSTRUCTION (The "Madara" Layout)
    # ------------------------------------------------------
    def create_menu_bar(self):
        # A classic, non-intrusive top menu
        menu_bar = Menu(self, bg=OpenShotStyleConfig.BG_PANEL, fg="white")
        
        file_menu = Menu(menu_bar, tearoff=0, bg="#333", fg="white")
        file_menu.add_command(label="Import Media Project...", command=self.load_video)
        file_menu.add_separator()
        file_menu.add_command(label="Render & Export...", command=self.export_video)
        file_menu.add_command(label="Exit Studio", command=self.on_close)
        
        tools_menu = Menu(menu_bar, tearoff=0, bg="#333", fg="white")
        tools_menu.add_command(label="AI: Auto-Caption", command=self.start_ai_transcription)
        tools_menu.add_command(label="Audio: Denoise (Coming Soon)", command=lambda: print("Stub"))

        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="Tools", menu=tools_menu)
        self.config(menu=menu_bar)

    def create_layout(self):
        """ Uses a professional 3-Row Grid architecture """
        self.grid_rowconfigure(0, weight=6) # Asset Browser + Preview
        self.grid_rowconfigure(1, weight=0) # Control Bar (Fixed Height)
        self.grid_rowconfigure(2, weight=4) # Timeline Area
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2) # Preview is dominant width
        
        # --- TOP LEFT: ASSET MANAGER ---
        self.tab_panel = ctk.CTkTabview(self, fg_color=OpenShotStyleConfig.BG_PANEL, corner_radius=6)
        self.tab_panel.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        self.tab_panel.add("Assets")
        self.tab_panel.add("Captions")
        
        # File List Treeview
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#333", foreground="white", fieldbackground="#333", borderwidth=0)
        style.configure("Treeview.Heading", background="#444", foreground="white", relief="flat")
        
        self.files_tree = ttk.Treeview(self.tab_panel.tab("Assets"), show="headings")
        self.files_tree["columns"] = ("file")
        self.files_tree.heading("file", text="Project Files")
        self.files_tree.pack(fill="both", expand=True)

        # Caption List Treeview
        self.cap_tree = ttk.Treeview(self.tab_panel.tab("Captions"), columns=("start", "text"), show="headings")
        self.cap_tree.heading("start", text="Time")
        self.cap_tree.column("start", width=60)
        self.cap_tree.heading("text", text="Content")
        self.cap_tree.pack(fill="both", expand=True)
        self.cap_tree.bind("<Double-1>", self.edit_segment_click) # Edit event

        # --- TOP RIGHT: VIDEO PREVIEW ---
        preview_cont = ctk.CTkFrame(self, fg_color="black")
        preview_cont.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        self.video_canvas = ctk.CTkCanvas(preview_cont, bg="black", highlightthickness=0)
        self.video_canvas.pack(fill="both", expand=True)
        
        self.lbl_overlay = ctk.CTkLabel(preview_cont, text="Drop Media Here", font=("Segoe UI", 24), text_color="#444")
        self.lbl_overlay.place(relx=0.5, rely=0.5, anchor="center")

        # --- MIDDLE: PLAYBACK CONTROLS ---
        toolbar = ctk.CTkFrame(self, fg_color=OpenShotStyleConfig.BG_PANEL, height=45)
        toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(0,5))
        
        ctrl_group = ctk.CTkFrame(toolbar, fg_color="transparent")
        ctrl_group.pack(anchor="center", pady=5)
        
        # Icons using text for compatibility, replace with Images later if desired
        self.btn_prev = ctk.CTkButton(ctrl_group, text="⏮", width=40, fg_color="#444", command=lambda: self.seek(-5))
        self.btn_prev.pack(side="left", padx=2)
        
        self.btn_play = ctk.CTkButton(ctrl_group, text="▶", width=50, fg_color=OpenShotStyleConfig.ACCENT_BLUE, command=self.toggle_play)
        self.btn_play.pack(side="left", padx=10)
        
        self.btn_next = ctk.CTkButton(ctrl_group, text="⏭", width=40, fg_color="#444", command=lambda: self.seek(5))
        self.btn_next.pack(side="left", padx=2)
        
        self.lbl_time = ctk.CTkLabel(ctrl_group, text="00:00:00", font=("Consolas", 14, "bold"))
        self.lbl_time.pack(side="left", padx=20)

        # --- BOTTOM: THE TIMELINE CANVAS ---
        self.tl_bg = ctk.CTkFrame(self, fg_color=OpenShotStyleConfig.BG_TIMELINE)
        self.tl_bg.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Track Header
        ctk.CTkLabel(self.tl_bg, text="  TRACKS  ", font=("Arial", 9, "bold"), text_color="#666").pack(anchor="w")
        
        self.tl_canvas = ctk.CTkCanvas(self.tl_bg, bg=OpenShotStyleConfig.BG_TIMELINE, 
                                       highlightthickness=0, cursor="hand2")
        self.tl_canvas.pack(fill="both", expand=True)
        
        self.tl_canvas.bind("<Button-1>", self.tl_click)
        self.tl_canvas.bind("<B1-Motion>", self.tl_drag)

    # ------------------------------------------------------
    # VIDEO LOGIC & ENGINE
    # ------------------------------------------------------
    def load_video(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi")])
        if not file_path: return
        
        self.video_path = file_path
        self.lbl_overlay.place_forget()
        
        # 1. Update UI Lists
        fname = os.path.basename(file_path)
        for i in self.files_tree.get_children(): self.files_tree.delete(i)
        self.files_tree.insert("", "end", values=(fname,))
        
        # 2. Load into VLC (Instant Playback)
        media = self.vlc_instance.media_new(file_path)
        self.media_player.set_media(media)
        self.media_player.set_hwnd(self.video_canvas.winfo_id())
        self.media_player.play()
        self.after(100, self.media_player.pause) # Pre-load frame
        
        # 3. Get precise metadata
        try:
            clip = VideoFileClip(self.video_path)
            self.duration = clip.duration
            clip.close() # Free resource
        except:
            self.duration = 60.0
            
        # 4. Generate Waveform (Threaded)
        self.generate_waveform()
        self.redraw_timeline()

    def toggle_play(self):
        if self.media_player.is_playing():
            self.media_player.pause()
            self.btn_play.configure(text="▶")
            self.is_playing = False
        else:
            self.media_player.play()
            self.btn_play.configure(text="⏸")
            self.is_playing = True

    def seek(self, sec):
        if not self.media_player: return
        t = self.media_player.get_time() + (sec * 1000)
        self.media_player.set_time(max(0, int(t)))
        self.redraw_timeline()

    def tl_click(self, event):
        """ Interactive Timeline Seeking """
        if self.duration <= 0: return
        width = self.tl_canvas.winfo_width()
        pct = event.x / width
        target_ms = int(pct * self.duration * 1000)
        self.media_player.set_time(target_ms)
        self.redraw_timeline()

    def tl_drag(self, event):
        self.tl_click(event)

    def update_ui_loop(self):
        """ High refresh rate UI Loop """
        if self.is_playing and self.media_player:
            current_ms = self.media_player.get_time()
            if current_ms >= 0:
                # Update timer
                sec = current_ms // 1000
                self.lbl_time.configure(text=f"{sec//3600:02}:{(sec%3600)//60:02}:{sec%60:02}")
                # Redraw playhead
                self.redraw_timeline()
        
        self.after(30, self.update_ui_loop) # 30fps UI updates

    # ------------------------------------------------------
    # VISUALIZATIONS (Rust/Native Canvas)
    # ------------------------------------------------------
    def generate_waveform(self):
        threading.Thread(target=self._wf_worker, daemon=True).start()

    def _wf_worker(self):
        try:
            if RUST_AVAILABLE:
                # Assuming Rust API: generate(path, points_count)
                print("Generating Waveform via Rust...")
                self.waveform_points = subtitle_engine.generate_waveform(self.video_path, 1000)
            else:
                # Faster Python approach (RMS Approximation)
                print("Generating Waveform via Python...")
                clip = AudioFileClip(self.video_path)
                points = 500
                chunk = clip.duration / points
                w_data = []
                for i in range(points):
                    t = i * chunk
                    # Only reading short frames for speed
                    try:
                        frame = clip.to_soundarray(tt=t, nbytes=2, fps=16000, buffersize=800)
                        vol = np.sqrt(np.mean(frame**2))
                        w_data.append(vol)
                    except: w_data.append(0)
                
                mx = max(w_data) if w_data else 1
                self.waveform_points = [x/mx for x in w_data]
                clip.close()
            
            self.after(0, self.redraw_timeline)
        except Exception as e:
            print(f"Waveform Fail: {e}")

    def redraw_timeline(self):
        self.tl_canvas.delete("all")
        w = self.tl_canvas.winfo_width()
        h = self.tl_canvas.winfo_height()
        
        track_h = 70
        
        # --- TRACK 1 (VIDEO/WAVEFORM) ---
        y1 = 20
        self._draw_track_bg(y1, track_h, w, "Track 2 (Media)", OpenShotStyleConfig.TRACK_VID_BG)
        
        if self.waveform_points:
            mid = y1 + (track_h/2)
            bar_w = w / len(self.waveform_points)
            
            # Draw waveform as one polygon for GPU speed (Canvas optimization)
            pts = []
            # Top line
            for i, val in enumerate(self.waveform_points):
                pts.extend([i*bar_w, mid - (val * 30)])
            # Bottom line (reverse)
            for i, val in reversed(list(enumerate(self.waveform_points))):
                pts.extend([i*bar_w, mid + (val * 30)])
                
            self.tl_canvas.create_polygon(pts, fill=OpenShotStyleConfig.TRACK_VID_FG, outline="")

        # --- TRACK 2 (CAPTIONS) ---
        y2 = y1 + track_h + 5
        self._draw_track_bg(y2, track_h, w, "Track 1 (Captions)", OpenShotStyleConfig.TRACK_SUB_BG)
        
        if self.subtitle_segments and self.duration > 0:
            px_sec = w / self.duration
            for seg in self.subtitle_segments:
                sx = seg['start'] * px_sec
                ex = seg['end'] * px_sec
                # Make tiny clips visible
                if ex - sx < 4: ex = sx + 4
                
                clip_y = y2 + 15
                clip_h = track_h - 30
                self.tl_canvas.create_rectangle(sx, clip_y, ex, clip_y+clip_h, 
                                                fill=OpenShotStyleConfig.TRACK_SUB_FG, outline="black")
                
                # Optimization: Only draw text if clip is wide enough
                if ex - sx > 40:
                    self.tl_canvas.create_text(sx+5, clip_y + (clip_h/2), 
                                               text=seg['text'], anchor="w", font=("Arial", 9), fill="black")

        # --- PLAYHEAD ---
        if self.media_player.get_time() >= 0 and self.duration > 0:
            play_x = (self.media_player.get_time() / 1000 / self.duration) * w
            self.tl_canvas.create_line(play_x, 0, play_x, h, fill=OpenShotStyleConfig.RED_PLAYHEAD, width=2)
            self.tl_canvas.create_polygon(play_x-5,0, play_x+5,0, play_x,15, fill=OpenShotStyleConfig.RED_PLAYHEAD)

    def _draw_track_bg(self, y, h, w, title, color):
        # Track base
        self.tl_canvas.create_rectangle(0, y, w, y+h, fill="#181818", outline="#333")
        # Clip placeholder area color
        # self.tl_canvas.create_rectangle(0, y+5, w, y+h-5, fill=color, stipple="gray12") 
        self.tl_canvas.create_text(5, y+8, text=title, fill=OpenShotStyleConfig.TEXT_GRAY, font=("Arial", 8), anchor="w")

    # ------------------------------------------------------
    # AI ENGINE
    # ------------------------------------------------------
    def start_ai_transcription(self):
        if not self.video_path: return
        self.lbl_overlay.configure(text="AI Processor Running...")
        self.lbl_overlay.place(relx=0.5, rely=0.5)
        threading.Thread(target=self._ai_task, daemon=True).start()

    def _ai_task(self):
        try:
            import whisper
            # Extract Audio first (safer than MoviePy piping sometimes)
            temp_audio = "temp_transcribe.wav"
            subprocess.run(f'ffmpeg -y -i "{self.video_path}" -ar 16000 -ac 1 -c:a pcm_s16le {temp_audio}', 
                           shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            model = whisper.load_model(self.ai_model.get())
            res = model.transcribe(temp_audio)
            self.subtitle_segments = res["segments"]
            
            try: os.remove(temp_audio) 
            except: pass
            
            self.after(0, self._finish_ai)
        except Exception as e:
            print(f"AI Failed: {e}")
            self.after(0, lambda: messagebox.showerror("AI Error", str(e)))

    def _finish_ai(self):
        self.lbl_overlay.place_forget()
        self.tab_panel.set("Captions")
        self.files_tree.selection_remove(self.files_tree.selection()) # Deselect
        
        # Fill treeview
        for i in self.cap_tree.get_children(): self.cap_tree.delete(i)
        for i, s in enumerate(self.subtitle_segments):
            t_str = f"{s['start']:.1f} -> {s['end']:.1f}"
            self.cap_tree.insert("", "end", iid=str(i), values=(t_str, s['text'].strip()))
            
        self.redraw_timeline()
        messagebox.showinfo("AI", "Transcription Complete")

    def edit_segment_click(self, event):
        """ Edit Caption via double click """
        sel = self.cap_tree.selection()
        if not sel: return
        idx = int(sel[0])
        current_text = self.subtitle_segments[idx]['text']
        
        # Move video to check
        start_ms = int(self.subtitle_segments[idx]['start'] * 1000)
        self.media_player.set_time(start_ms)
        
        new = simpledialog.askstring("Editor", "Subtitle Content:", initialvalue=current_text)
        if new:
            self.subtitle_segments[idx]['text'] = new
            t_str = f"{self.subtitle_segments[idx]['start']:.1f}"
            self.cap_tree.item(str(idx), values=(t_str, new))
            self.redraw_timeline()

    # ------------------------------------------------------
    # EXPORT ENGINE (UNFROZEN THREAD)
    # ------------------------------------------------------
    def export_video(self):
        if not self.video_path:
            messagebox.showerror("Err", "No video.")
            return
        
        out_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if not out_path: return

        # Disable interaction
        self.is_exporting = True
        self.export_win = ctk.CTkToplevel(self)
        self.export_win.title("Rendering...")
        self.export_win.geometry("300x100")
        self.export_lbl = ctk.CTkLabel(self.export_win, text="Initializing Renderer...")
        self.export_lbl.pack(expand=True)
        self.export_bar = ctk.CTkProgressBar(self.export_win)
        self.export_bar.pack(fill="x", padx=20, pady=10)
        self.export_bar.set(0)
        self.export_bar.start() # Indeterminate mode because MoviePy logging is hard to parse in real-time

        # Start thread
        threading.Thread(target=self._render_worker, args=(out_path,), daemon=True).start()

    def _render_worker(self, out_path):
        try:
            vid_clip = VideoFileClip(self.video_path)
            
            layers = [vid_clip]
            
            # Burn Captions (Basic)
            if self.subtitle_segments:
                print("Building Text Clips...")
                for s in self.subtitle_segments:
                    # IMPORTANT: Windows Users often fail here without ImageMagick
                    # Ensure you have 'magick' in PATH or use a simpler method
                    try:
                        # We assume Arial as a safe default. 
                        txt = (TextClip(s['text'], fontsize=55, color='white', 
                                        font='Arial', stroke_color='black', stroke_width=2, method='caption', size=(vid_clip.w*0.8, None))
                               .set_position(('center', 'bottom'))
                               .set_duration(s['end'] - s['start'])
                               .set_start(s['start']))
                        layers.append(txt)
                    except Exception as txt_err:
                        print(f"Skipped text clip: {txt_err}")

            final = CompositeVideoClip(layers)
            
            # Writing file (The Slow Part)
            # Using a lower preset for speed during testing
            final.write_videofile(out_path, codec='libx264', audio_codec='aac', preset="fast", 
                                  logger=None) # logger=None prevents console spam, use manual progress if desired
            
            # Cleanup
            vid_clip.close()
            self.after(0, self._export_success)
            
        except Exception as e:
            self.export_error = str(e)
            self.after(0, self._export_fail)

    def _export_success(self):
        self.export_win.destroy()
        self.is_exporting = False
        messagebox.showinfo("Success", "Video Exported Successfully!")

    def _export_fail(self):
        self.export_win.destroy()
        self.is_exporting = False
        messagebox.showerror("Render Error", f"Engine Failure:\n{self.export_error}")

    # ------------------------------------------------------
    # SYSTEM HANDLERS
    # ------------------------------------------------------
    def on_window_resize(self, event):
        if event.widget == self.tl_canvas:
            self.redraw_timeline()

    def on_close(self):
        # Clean shutdown
        try:
            if self.media_player:
                self.media_player.stop()
                self.media_player.release()
            self.destroy()
            os._exit(0) # Force thread kill
        except:
            self.destroy()

if __name__ == "__main__":
    app = OpenShotEditorApp()
    app.mainloop()