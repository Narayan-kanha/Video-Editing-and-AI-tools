import sys
import os
import vlc #type: ignore
from PySide6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QWidget, 
                               QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
                               QFrame, QPushButton, QGraphicsView, QGraphicsScene, 
                               QStyle, QFileDialog, QSlider)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPen, QIcon

# =====================================================
#  THE "PRO" ADOBE STYLE (RESTORED)
# =====================================================
ADOBE_STYLESHEET = """
QMainWindow {
    background-color: #1d1d1d;
}
QDockWidget {
    border: 1px solid #000;
    titlebar-close-icon: url(none);
    titlebar-normal-icon: url(none);
}
QDockWidget::title {
    background: #2d2d2d;
    padding-left: 8px;
    padding-top: 4px;
    padding-bottom: 4px;
    color: #bbb;
    font-weight: bold;
    font-size: 11px;
    font-family: 'Segoe UI';
    border-bottom: 1px solid #000;
}
/* BUTTONS */
QPushButton.transport {
    background-color: transparent;
    border: none;
    color: #ddd;
    font-size: 16px;
    font-weight: bold;
}
QPushButton.transport:hover { color: #3997f3; }

/* LISTS */
QTreeWidget { 
    background-color: #1e1e1e; 
    border: none; 
    color: #ccc; 
    font-size: 11px;
}
QHeaderView::section {
    background-color: #2d2d2d;
    color: #aaa;
    border: none;
    border-right: 1px solid #111;
    padding: 4px;
}

/* TIMELINE & SCROLL */
QSlider::groove:horizontal {
    height: 4px;
    background: #333;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #3997f3;
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QFrame#TimelineHeader { background-color: #2b2b2b; border-right: 1px solid #444; }
QFrame#TrackControl { background-color: #262626; border-bottom: 1px solid #1a1a1a; min-height: 50px; }
"""

class KanhaStudioPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kanha Studio 2025 (Adobe Edition)")
        self.resize(1920, 1080)
        self.setStyleSheet(ADOBE_STYLESHEET)
        
        # --- LOGIC ENGINE (VLC) ---
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_ui)

        # --- LAYOUT ENGINE ---
        # This makes the docks behave like panels
        self.setDockOptions(QMainWindow.AllowNestedDocks | QMainWindow.AnimatedDocks)
        
        # These settings FORCE the left tool strip to go all the way down
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)

        self.create_menus()
        self.build_layout()
        
        # Force the sizes AFTER the UI is built
        self.setup_pro_grid()

    def create_menus(self):
        bar = self.menuBar()
        bar.setStyleSheet("background-color: #1d1d1d; color: #ccc; font-size: 12px;")
        bar.addMenu("File").addAction("Import Media...", self.import_file)
        bar.addMenu("Edit")
        bar.addMenu("Sequence")

    def build_layout(self):
        # 1. TOOLS (Left Strip)
        self.dock_tools = QDockWidget("Tools", self)
        self.dock_tools.setFixedWidth(40)
        self.dock_tools.setTitleBarWidget(QWidget()) # Hides titlebar completely
        self.dock_tools.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dock_tools.setWidget(self.make_tool_strip())
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_tools)

        # 2. PROJECT BIN
        self.dock_project = QDockWidget("Project: Kanha_Edit", self)
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabels(["Name", "Details", "Type"])
        self.project_tree.itemDoubleClicked.connect(self.on_project_double_click)
        self.dock_project.setWidget(self.project_tree)
        self.dock_project.setObjectName("D_Project")

        # 3. TIMELINE
        self.dock_timeline = QDockWidget("Sequence 01", self)
        self.dock_timeline.setWidget(self.make_timeline())
        self.dock_timeline.setObjectName("D_Timeline")

        # 4. SOURCE MONITOR
        self.dock_source = QDockWidget("Source: (No Clip)", self)
        src_lbl = QLabel("Source Monitor", alignment=Qt.AlignCenter)
        src_lbl.setStyleSheet("background: #000;")
        self.dock_source.setWidget(src_lbl)
        self.dock_source.setObjectName("D_Source")

        # 5. PROGRAM MONITOR (Video Player)
        self.dock_program = QDockWidget("Program: Sequence 01", self)
        self.dock_program.setWidget(self.make_program_monitor())
        self.dock_program.setObjectName("D_Program")

        # Don't add docks yet, run setup_pro_grid

    def setup_pro_grid(self):
        """ The Logic that creates the exact Adobe Layout """
        # 1. Add Timeline at bottom
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_timeline)
        
        # 2. Put Project Bin to the LEFT of Timeline
        self.splitDockWidget(self.dock_timeline, self.dock_project, Qt.Horizontal)
        
        # 3. Add Program to Top
        self.addDockWidget(Qt.TopDockWidgetArea, self.dock_program)
        
        # 4. Put Source to LEFT of Program
        self.splitDockWidget(self.dock_program, self.dock_source, Qt.Horizontal)

        # 5. Set Dimensions (Simulated)
        # Timeline/Project should take up bottom 40%
        # Project bin width ~400px
        self.resizeDocks([self.dock_project, self.dock_timeline], [400, 1200], Qt.Horizontal)
        self.resizeDocks([self.dock_program, self.dock_timeline], [500, 400], Qt.Vertical)

    # --- WIDGET MAKERS ---

    def make_program_monitor(self):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        # Video Surface
        self.video_surface = QFrame()
        self.video_surface.setStyleSheet("background-color: black; border: 1px solid #111;")
        layout.addWidget(self.video_surface)
        
        # Controls Area
        controls = QFrame()
        controls.setStyleSheet("background: #1d1d1d; min-height: 35px; border-top: 1px solid #000;")
        h_layout = QHBoxLayout(controls)
        h_layout.setContentsMargins(10, 0, 10, 0)
        
        self.tc_lbl = QLabel("00:00:00:00")
        self.tc_lbl.setStyleSheet("color: #3997f3; font-family: Consolas; font-weight: bold;")
        h_layout.addWidget(self.tc_lbl)
        
        h_layout.addStretch()
        
        # Play/Pause buttons
        for icon, func in [("⏪", None), ("▶", self.toggle_play), ("⏩", None), ("📷", None)]:
            btn = QPushButton(icon)
            btn.setProperty("class", "transport")
            if func: btn.clicked.connect(func)
            h_layout.addWidget(btn)
            
        h_layout.addStretch()
        
        # Timeline Scrubber under controls or above? Premiere puts controls *under* video
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(self.pause_video)
        self.slider.sliderReleased.connect(self.seek_video)
        
        layout.addWidget(self.slider)
        layout.addWidget(controls)
        return frame

    def make_timeline(self):
        container = QFrame()
        l = QHBoxLayout(container)
        l.setContentsMargins(0,0,0,0); l.setSpacing(0)
        
        # Headers
        headers = QFrame()
        headers.setObjectName("TimelineHeader")
        headers.setFixedWidth(100)
        v = QVBoxLayout(headers); v.setSpacing(1); v.setContentsMargins(0,0,0,0)
        
        for name in ["V3", "V2", "V1", "", "A1", "A2", "A3"]:
            row = QFrame()
            if name: 
                row.setObjectName("TrackControl")
                lbl = QLabel(name)
                lbl.setStyleSheet("color: #777; padding-left: 5px; font-weight: bold;")
                box = QVBoxLayout(row); box.addWidget(lbl); box.setAlignment(Qt.AlignVCenter)
            else:
                row.setStyleSheet("background: #222; max-height: 20px;")
            v.addWidget(row)
        v.addStretch()
        
        # Tracks
        tracks = QFrame()
        tracks.setStyleSheet("background: #181818;")
        # Placeholder Logic
        ctr = QVBoxLayout(tracks)
        lbl = QLabel("Sequences Go Here")
        lbl.setStyleSheet("color: #333; font-size: 30px; font-weight: bold;")
        lbl.setAlignment(Qt.AlignCenter)
        ctr.addWidget(lbl)
        
        l.addWidget(headers)
        l.addWidget(tracks)
        return container

    def make_tool_strip(self):
        f = QFrame()
        v = QVBoxLayout(f)
        v.setContentsMargins(0,10,0,10)
        for i in ["⬉", "◫", "✄", "✎", "✋", "🔍"]:
            b = QPushButton(i)
            b.setFixedSize(30,30)
            b.setStyleSheet("background: transparent; border: none; color: #aaa; font-size: 16px;")
            v.addWidget(b)
        v.addStretch()
        return f

    # --- LOGIC ---

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Video (*.mp4 *.mov *.mkv)")
        if path:
            name = os.path.basename(path)
            item = QTreeWidgetItem([name, "Movie"])
            item.setData(0, Qt.UserRole, path)
            
            icon = self.style().standardIcon(QStyle.SP_FileIcon)
            item.setIcon(0, icon)
            self.project_tree.addTopLevelItem(item)
            
            # Auto-load first clip
            self.load_media(path)

    def on_project_double_click(self, item, col):
        path = item.data(0, Qt.UserRole)
        if path: self.load_media(path)

    def load_media(self, path):
        self.player.stop()
        m = self.vlc_instance.media_new(path)
        self.player.set_media(m)
        
        # LINK VLC TO QT WIDGET
        if sys.platform == "win32":
            self.player.set_hwnd(int(self.video_surface.winId()))
        
        self.player.play()
        self.timer.start()

    def toggle_play(self):
        if self.player.is_playing(): self.player.pause()
        else: self.player.play()

    def pause_video(self): self.player.pause()
    def seek_video(self):
        pos = self.slider.value()
        self.player.set_position(pos / 1000.0)
        self.player.play()

    def update_ui(self):
        if self.player.is_playing() and not self.slider.isSliderDown():
            self.slider.setValue(int(self.player.get_position() * 1000))
            
            ms = self.player.get_time()
            sec = max(0, ms // 1000)
            m, s = divmod(sec, 60)
            self.tc_lbl.setText(f"00:{m:02}:{s:02}:00")

    def closeEvent(self, e):
        self.player.stop()
        e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = KanhaStudioPro()
    window.show()
    
    sys.exit(app.exec())