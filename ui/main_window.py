import sys
import os
import vlc # type: ignore
from PySide6.QtWidgets import (QMainWindow, QDockWidget, QLabel, QWidget, QFileDialog, QApplication, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QSettings

# Import Widgets
from .styles import ADOBE_STYLESHEET
from .widgets.program_monitor import ProgramMonitor
from .widgets.project_bin import ProjectBin
from .widgets.timeline import Timeline
from .widgets.tools import ToolStrip
from .widgets.effects_panel import EffectsPanel        # <--- NEW
from .widgets.properties_panel import PropertiesPanel  # <--- NEW

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kanha Studio 2025 - Fully Customizable")
        self.resize(1600, 900)
        self.setStyleSheet(ADOBE_STYLESHEET)
        
        # Settings Manager (Persistent Layouts)
        self.settings = QSettings("Kanha", "StudioPro")

        # --- CORE LOGIC ---
        self.vlc_inst = vlc.Instance()
        self.player = self.vlc_inst.media_player_new()
        
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_clock)

        # --- INIT UI ---
        # 1. Docking Logic
        self.setDockOptions(QMainWindow.AllowNestedDocks | QMainWindow.AnimatedDocks)
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        
        # 2. Build Widgets
        self.init_docks()
        
        # 3. Build Menus (Dependent on Docks existing)
        self.create_menus()
        
        # 4. Load Layout
        self.restore_user_layout()
        
        self.init_logic_connections()

    def init_docks(self):
        self.docks = {} # Keep track of docks for menus

        # TOOL STRIP
        self.dock_tools = self.create_dock("Tools", ToolStrip(), area=Qt.LeftDockWidgetArea)
        self.dock_tools.setFixedWidth(40)
        self.dock_tools.setTitleBarWidget(QWidget()) # No title bar
        self.dock_tools.setFeatures(QDockWidget.NoDockWidgetFeatures) # Locked

        # PROJECT BIN
        self.bin_widget = ProjectBin()
        self.dock_project = self.create_dock("Project Files", self.bin_widget, "ProjectBin")

        # TIMELINE
        self.timeline_widget = Timeline()
        self.dock_timeline = self.create_dock("Timeline", self.timeline_widget, "Timeline")
        
        # EFFECTS
        self.effects_widget = EffectsPanel()
        self.dock_effects = self.create_dock("Effects Library", self.effects_widget, "Effects")

        # SOURCE
        self.dock_source = self.create_dock("Source Monitor", QLabel("No Clip Loaded"), "Source")

        # PROPERTIES (Font/Effects)
        self.props_widget = PropertiesPanel()
        self.dock_props = self.create_dock("Effect Controls", self.props_widget, "Properties")

        # PROGRAM
        self.monitor_widget = ProgramMonitor()
        self.dock_program = self.create_dock("Program Monitor", self.monitor_widget, "Program")

    def create_dock(self, name, widget, object_name=None, area=None):
        dock = QDockWidget(name, self)
        dock.setWidget(widget)
        if object_name: dock.setObjectName(object_name)
        
        if area:
            self.addDockWidget(area, dock)
            
        self.docks[name] = dock
        return dock

    def create_menus(self):
        bar = self.menuBar()
        bar.setStyleSheet("background-color: #1d1d1d; color: #ccc;")
        
        file = bar.addMenu("File")
        file.addAction("Import Media...", self.import_file)
        file.addSeparator()
        file.addAction("Save Project State", self.save_current_layout)
        file.addAction("Exit", self.close)

        # THE VIEW BAR (Toggle Panels)
        view = bar.addMenu("Window")
        
        # Qt's toggleViewAction() automagically handles checks/visibility
        for name, dock in self.docks.items():
            view.addAction(dock.toggleViewAction())
            
        view.addSeparator()
        
        ws_menu = view.addMenu("Workspaces")
        ws_menu.addAction("Reset to Default Editing", self.reset_to_default_editing)
        ws_menu.addAction("Reset to Effects", self.reset_to_effects_layout)

    # -----------------------------
    # LAYOUT ENGINE (Save/Load)
    # -----------------------------
    def reset_to_default_editing(self):
        # 1. Timeline Bottom
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_timeline)
        
        # 2. Bin Left of Timeline
        self.splitDockWidget(self.dock_timeline, self.dock_project, Qt.Horizontal)
        self.dock_project.show()
        
        # 3. Effects Left of Project (Stacked)
        self.tabifyDockWidget(self.dock_project, self.dock_effects)
        
        # 4. Program Top Right
        self.addDockWidget(Qt.TopDockWidgetArea, self.dock_program)
        self.dock_program.show()
        
        # 5. Source Left of Program
        self.splitDockWidget(self.dock_program, self.dock_source, Qt.Horizontal)
        self.dock_source.show()
        
        # 6. Properties Tabbed with Source
        self.tabifyDockWidget(self.dock_source, self.dock_props)
        self.dock_props.show()
        
        # Sizing
        self.resizeDocks([self.dock_project, self.dock_timeline], [400, 1200], Qt.Horizontal)

    def reset_to_effects_layout(self):
        # Different arrangement prioritizing effects
        self.splitDockWidget(self.dock_program, self.dock_props, Qt.Horizontal)
        self.dock_effects.show()
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_effects)

    def restore_user_layout(self):
        # Check if saved data exists
        saved_state = self.settings.value("windowState")
        saved_geom = self.settings.value("geometry")
        
        if saved_state:
            self.restoreState(saved_state)
            self.restoreGeometry(saved_geom)
        else:
            # First Run
            self.reset_to_default_editing()

    def save_current_layout(self):
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("geometry", self.saveGeometry())

    def closeEvent(self, e):
        # Auto-Save Layout on Close
        self.save_current_layout()
        self.player.stop()
        e.accept()

    # -------------------------------
    # LOGIC (Player Wires)
    # -------------------------------
    def init_logic_connections(self):
        self.bin_widget.itemDoubleClicked.connect(self.load_media_from_bin)
        self.monitor_widget.btn_play.clicked.connect(self.toggle_play)
        self.monitor_widget.slider.sliderPressed.connect(self.pause)
        self.monitor_widget.slider.sliderReleased.connect(self.seek)

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Video (*.mp4 *.mov *.mkv *.avi)")
        if path:
            name = os.path.basename(path)
            self.bin_widget.add_item(name, "File", path)
            self.load_media(path)

    def load_media_from_bin(self, item, col):
        path = item.data(0, Qt.UserRole)
        if path: self.load_media(path)

    def load_media(self, path):
        self.player.stop()
        m = self.vlc_inst.media_new(path)
        self.player.set_media(m)
        win_id = int(self.monitor_widget.video_surface.winId())
        if sys.platform == "win32": self.player.set_hwnd(win_id)
        else: self.player.set_xwindow(win_id)
        self.player.play()
        self.timer.start()

    def toggle_play(self):
        if self.player.is_playing(): self.player.pause()
        else: self.player.play()

    def pause(self): self.player.pause()
    def seek(self):
        pos = self.monitor_widget.slider.value()
        self.player.set_position(pos / 1000.0)
        self.player.play()

    def update_clock(self):
        if self.player.is_playing() and not self.monitor_widget.slider.isSliderDown():
            pos = self.player.get_position()
            self.monitor_widget.slider.setValue(int(pos * 1000))
            ms = self.player.get_time()
            sec = max(0, ms // 1000)
            m, s = divmod(sec, 60)
            self.monitor_widget.lbl_time.setText(f"00:{m:02}:{s:02}:00")