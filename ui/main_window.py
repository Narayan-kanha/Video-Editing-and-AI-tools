import sys
import os
import vlc # type: ignore
from PySide6.QtWidgets import (QMainWindow, QDockWidget, QLabel, QWidget, 
                               QFileDialog, QApplication, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QSettings

# Import ALL your widgets
from .styles import ADOBE_STYLESHEET
from .widgets.program_monitor import ProgramMonitor
from .widgets.project_bin import ProjectBin
from .widgets.timeline import Timeline  # (The one with Rust Waveforms)
from .widgets.tools import ToolStrip
from .widgets.effects_panel import EffectsPanel
from .widgets.properties_panel import PropertiesPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kanha Studio 2025 - Pro")
        self.resize(1600, 900)
        self.setStyleSheet(ADOBE_STYLESHEET)
        
        # Persistent Settings (Layout Memory)
        self.settings = QSettings("KanhaStudios", "KanhaEditor")

        # --- VLC ENGINE ---
        self.vlc_inst = vlc.Instance()
        self.player = self.vlc_inst.media_player_new()
        
        # Playback Timer (50ms updates)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_ui_from_player)

        # --- GUI BUILDER ---
        # 1. Enable Advanced Docking
        self.setDockOptions(QMainWindow.AllowNestedDocks | QMainWindow.AnimatedDocks)
        # Make left/right docks occupy the corners (Full Height)
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        
        # 2. Instantiate All Panels
        self.create_docks()
        
        # 3. Build The Menu Bar
        self.create_menus()
        
        # 4. Restore Previous Layout (or Default)
        self.restore_layout_state()
        
        # 5. Connect Signals (Clicks, drags, etc.)
        self.init_connections()

    def create_docks(self):
        """ Initializes the 7 Dockable Panels """
        self.docks_list = {} # Dictionary to track docks for Menus

        # A. Tools (Left Strip)
        self.dock_tools = QDockWidget("Tools", self)
        self.dock_tools.setFixedWidth(40)
        self.dock_tools.setTitleBarWidget(QWidget()) # Hide title bar
        self.dock_tools.setFeatures(QDockWidget.NoDockWidgetFeatures) # Locked
        self.dock_tools.setWidget(ToolStrip())
        self.dock_tools.setObjectName("Tools") # Vital for restoreState
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_tools)
        self.docks_list["Tools"] = self.dock_tools

        # B. Project Bin (Assets)
        self.bin_widget = ProjectBin()
        self.dock_project = self.wrap_in_dock("Project Bin", self.bin_widget, "ProjectBin")

        # C. Timeline (Visualization)
        self.timeline_widget = Timeline()
        self.dock_timeline = self.wrap_in_dock("Timeline", self.timeline_widget, "Timeline")
        
        # D. Effects Panel
        self.effects_widget = EffectsPanel()
        self.dock_effects = self.wrap_in_dock("Effects", self.effects_widget, "Effects")

        # E. Source Monitor (Clip Preview)
        # For now, just a placeholder black box
        src_lbl = QLabel("No Clip Selected")
        src_lbl.setAlignment(Qt.AlignCenter)
        src_lbl.setStyleSheet("background:black; color:#555;")
        self.dock_source = self.wrap_in_dock("Source Monitor", src_lbl, "Source")

        # F. Properties Panel (Font/Motion)
        self.props_widget = PropertiesPanel()
        self.dock_props = self.wrap_in_dock("Effect Controls", self.props_widget, "Properties")

        # G. Program Monitor (Main Video Player)
        self.monitor_widget = ProgramMonitor()
        self.dock_program = self.wrap_in_dock("Program Monitor", self.monitor_widget, "Program")

    def wrap_in_dock(self, title, widget, obj_name):
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setObjectName(obj_name) # Vital for persistence
        # Add to list for View Menu
        self.docks_list[title] = dock
        return dock

    def create_menus(self):
        bar = self.menuBar()
        bar.setStyleSheet("background-color: #1d1d1d; color: #ccc;")
        
        # FILE
        file = bar.addMenu("File")
        file.addAction("Import Media...", self.import_file)
        file.addSeparator()
        file.addAction("Save Workspace", self.save_layout_state)
        file.addAction("Exit", self.close)
        
        # EDIT
        edit = bar.addMenu("Edit")
        edit.addAction("Undo")
        edit.addAction("Redo")
        edit.addSeparator()
        edit.addAction("Preferences")

        # WINDOW (Toggle Panels)
        window = bar.addMenu("Window")
        # Workspaces Submenu
        ws = window.addMenu("Workspaces")
        ws.addAction("Reset to Editing", self.reset_layout_editing)
        ws.addAction("Reset to Color/Effects", self.reset_layout_effects)
        window.addSeparator()
        
        # Panel Toggles (Auto-syncs with dock visibility)
        for title, dock in self.docks_list.items():
            window.addAction(dock.toggleViewAction())

    # ------------------------------------------
    #  LAYOUT MANAGEMENT (The "Customizable" part)
    # ------------------------------------------
    def reset_layout_editing(self):
        """ Adobe Premiere Standard Layout """
        # 1. Timeline Bottom, Project Left Bottom
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_timeline)
        self.splitDockWidget(self.dock_timeline, self.dock_project, Qt.Horizontal)
        
        # 2. Effects Tabbed with Project
        self.tabifyDockWidget(self.dock_project, self.dock_effects)
        
        # 3. Program Top Right
        self.addDockWidget(Qt.TopDockWidgetArea, self.dock_program)
        
        # 4. Source Top Left
        self.splitDockWidget(self.dock_program, self.dock_source, Qt.Horizontal)
        
        # 5. Properties Tabbed with Source
        self.tabifyDockWidget(self.dock_source, self.dock_props)
        
        # Ensure everything is visible
        for dock in self.docks_list.values(): dock.setVisible(True)
        self.dock_project.raise_() # Bring Bin to front
        self.dock_source.raise_()  # Bring Source to front

        # Resize Logic (approx 40% left / 60% right)
        self.resizeDocks([self.dock_project, self.dock_timeline], [500, 1100], Qt.Horizontal)

    def reset_layout_effects(self):
        """ Layout optimized for Effects Work """
        # Move Effects Panel to Right column
        self.splitDockWidget(self.dock_program, self.dock_effects, Qt.Horizontal)
        self.dock_effects.show()
        # Bring Properties to front on the left
        self.dock_props.raise_()

    def save_layout_state(self):
        self.settings.setValue("state", self.saveState())
        self.settings.setValue("geometry", self.saveGeometry())

    def restore_layout_state(self):
        state = self.settings.value("state")
        geo = self.settings.value("geometry")
        
        if state:
            self.restoreGeometry(geo)
            self.restoreState(state)
        else:
            self.reset_layout_editing()

    def closeEvent(self, e):
        self.player.stop()
        self.save_layout_state()
        super().closeEvent(e)

    # ------------------------------------------
    #  CORE LOGIC (Loading, Playing, Updating)
    # ------------------------------------------
    def init_connections(self):
        # 1. File IO
        self.bin_widget.itemDoubleClicked.connect(self.on_bin_double_click)
        
        # 2. Transport
        self.monitor_widget.btn_play.clicked.connect(self.toggle_play)
        self.monitor_widget.slider.sliderPressed.connect(self.pause_user_seek)
        self.monitor_widget.slider.sliderReleased.connect(self.perform_seek)

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Video", "", "Video (*.mp4 *.mov *.mkv *.avi)")
        if path:
            filename = os.path.basename(path)
            self.bin_widget.add_item(filename, "Video", path)
            # Auto-Load
            self.load_media(path)

    def on_bin_double_click(self, item, col):
        path = item.data(0, Qt.UserRole)
        if path: self.load_media(path)

    def load_media(self, path):
        # Reset Logic
        self.player.stop()
        
        # Load VLC Media
        media = self.vlc_inst.media_new(path)
        self.player.set_media(media)
        
        # Bind to Window
        win_id = int(self.monitor_widget.video_surface.winId())
        if sys.platform == "win32":
            self.player.set_hwnd(win_id)
        elif sys.platform.startswith("linux"):
            self.player.set_xwindow(win_id)
            
        # Play
        self.player.play()
        self.timer.start()
        
        # --- TRIGGER RUST TIMELINE GENERATION ---
        # This sends the file path to the Timeline widget, 
        # which starts the background Rust thread.
        self.timeline_widget.load_waveform(path)

    def toggle_play(self):
        if self.player.is_playing(): self.player.pause()
        else: self.player.play()

    def pause_user_seek(self):
        """ Pause video when dragging slider so it doesn't stutter """
        self.player.pause()

    def perform_seek(self):
        pos = self.monitor_widget.slider.value()
        target = pos / 1000.0
        self.player.set_position(target)
        self.player.play()

    def update_ui_from_player(self):
        """ Called every 50ms to sync UI with Video State """
        if self.player.is_playing() and not self.monitor_widget.slider.isSliderDown():
            # Update Slider
            pos = self.player.get_position()
            self.monitor_widget.slider.setValue(int(pos * 1000))
            
            # Update Timecode
            ms = self.player.get_time()
            seconds = max(0, ms // 1000)
            m, s = divmod(seconds, 60)
            # Simple Frame fake logic (assuming 30fps)
            f = int((ms % 1000) / 33.33)
            
            time_str = f"{m:02}:{s:02}:{f:02}"
            self.monitor_widget.lbl_time.setText(time_str)