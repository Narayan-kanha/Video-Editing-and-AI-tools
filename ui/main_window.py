# ui/main_window.py
import sys
import os
import vlc  # type: ignore
from PySide6.QtWidgets import (QMainWindow, QDockWidget, QLabel, QWidget, QFileDialog)
from PySide6.QtCore import Qt, QTimer

# Import Local Assets
from .styles import ADOBE_STYLESHEET
from .widgets.program_monitor import ProgramMonitor
from .widgets.project_bin import ProjectBin
from .widgets.timeline import Timeline
from .widgets.tools import ToolStrip

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kanha Studio 2025 - Pro Modular")
        self.resize(1600, 900)
        self.setStyleSheet(ADOBE_STYLESHEET)
        
        # --- CORE LOGIC (VLC) ---
        self.vlc_inst = vlc.Instance()
        self.player = self.vlc_inst.media_player_new()
        
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_clock)

        # --- LAYOUT ---
        self.init_layout()
        self.init_logic_connections()

    def init_layout(self):
        # Enable docking magic
        self.setDockOptions(QMainWindow.AllowNestedDocks | QMainWindow.AnimatedDocks)
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)

        # Menu
        self.create_menu()

        # 1. Tool Strip (Left)
        self.dock_tools = QDockWidget("Tools", self)
        self.dock_tools.setTitleBarWidget(QWidget())
        self.dock_tools.setFixedWidth(40)
        self.dock_tools.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dock_tools.setWidget(ToolStrip())
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_tools)

        # 2. Project Bin (Left Bottom)
        self.dock_project = QDockWidget("Project: Kanha_Edit", self)
        self.bin_widget = ProjectBin() # Using our modular class
        self.dock_project.setWidget(self.bin_widget)

        # 3. Timeline (Bottom)
        self.dock_timeline = QDockWidget("Sequence 01", self)
        self.dock_timeline.setWidget(Timeline())

        # 4. Source Monitor (Top Leftish)
        self.dock_source = QDockWidget("Source: (No Clip)", self)
        self.dock_source.setWidget(QLabel("(No Clip Loaded)", alignment=Qt.AlignCenter))
        self.dock_source.setStyleSheet("background: black;")

        # 5. Program Monitor (Top Right) - Main Video
        self.dock_program = QDockWidget("Program: Sequence 01", self)
        self.monitor_widget = ProgramMonitor() # Using our modular class
        self.dock_program.setWidget(self.monitor_widget)

        # --- APPLY THE GRID LAYOUT ---
        # Start bottom
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_timeline)
        # Split Bottom
        self.splitDockWidget(self.dock_timeline, self.dock_project, Qt.Horizontal)
        # Add Top
        self.addDockWidget(Qt.TopDockWidgetArea, self.dock_program)
        # Split Top
        self.splitDockWidget(self.dock_program, self.dock_source, Qt.Horizontal)

        # Resize ratios
        self.resizeDocks([self.dock_project, self.dock_timeline], [400, 1200], Qt.Horizontal)
        self.resizeDocks([self.dock_program, self.dock_timeline], [550, 400], Qt.Vertical)

    def create_menu(self):
        bar = self.menuBar()
        bar.setStyleSheet("background-color: #1d1d1d; color: #ccc; font-size: 12px;")
        bar.addMenu("File").addAction("Import Media...", self.import_file)
        bar.addMenu("Edit")
        bar.addMenu("Sequence")

    # -------------------------------
    # LOGIC BINDING (Wires)
    # -------------------------------
    def init_logic_connections(self):
        # Connect Project Bin clicks to Player
        self.bin_widget.itemDoubleClicked.connect(self.load_media_from_bin)
        
        # Connect Player Controls to Player
        self.monitor_widget.btn_play.clicked.connect(self.toggle_play)
        
        # Connect Slider (Seek)
        self.monitor_widget.slider.sliderPressed.connect(self.pause)
        self.monitor_widget.slider.sliderReleased.connect(self.seek)

    # -------------------------------
    # MEDIA ENGINE
    # -------------------------------
    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Video (*.mp4 *.mov *.mkv *.avi)")
        if path:
            filename = os.path.basename(path)
            self.bin_widget.add_item(filename, "Imported", path)
            
            # Auto Load first clip logic
            self.load_media(path)

    def load_media_from_bin(self, item, column):
        path = item.data(0, 32) # 32 is UserRole
        if path:
            self.load_media(path)

    def load_media(self, path):
        self.player.stop()
        m = self.vlc_inst.media_new(path)
        self.player.set_media(m)
        
        # BIND VLC to the QFrame inside ProgramMonitor
        win_id = int(self.monitor_widget.video_surface.winId())
        
        if sys.platform == "win32":
            self.player.set_hwnd(win_id)
        else:
            self.player.set_xwindow(win_id)
            
        self.player.play()
        self.timer.start()

    def toggle_play(self):
        if self.player.is_playing(): self.player.pause()
        else: self.player.play()

    def pause(self):
        self.player.pause()

    def seek(self):
        pos = self.monitor_widget.slider.value()
        target = pos / 1000.0
        self.player.set_position(target)
        self.player.play()

    def update_clock(self):
        # Called every 50ms by Timer
        if self.player.is_playing() and not self.monitor_widget.slider.isSliderDown():
            # 1. Update Slider
            pos = self.player.get_position()
            self.monitor_widget.slider.setValue(int(pos * 1000))
            
            # 2. Update Time Label
            ms = self.player.get_time()
            sec = max(0, ms // 1000)
            m, s = divmod(sec, 60)
            self.monitor_widget.lbl_time.setText(f"00:{m:02}:{s:02}:00")

    def closeEvent(self, e):
        self.player.stop()
        e.accept()