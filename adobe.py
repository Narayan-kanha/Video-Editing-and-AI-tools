import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QWidget, 
                               QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
                               QFrame, QPushButton, QGraphicsView, QGraphicsScene, QStyle, QSizePolicy)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPen

# =====================================================
#  THE ADOBE STYLING (Tweaked for visibility)
# =====================================================
ADOBE_STYLESHEET = """
QMainWindow {
    background-color: #1d1d1d;
}
/* SEPARATORS & DOCKS */
QDockWidget {
    border: 1px solid #000;
    titlebar-close-icon: url(none); /* Hide close button to keep layout rigid */
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
/* TAB STYLING (For the panels) */
QTabWidget::pane { border: 1px solid #333; background: #1e1e1e; }
QTabBar::tab {
    background: #252525;
    color: #888;
    padding: 6px 12px;
    font-family: 'Segoe UI';
    font-size: 11px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
}
QTabBar::tab:selected {
    background: #383838;
    color: #ddd;
    border-top: 2px solid #3997f3;
}

/* TIMELINE TRACKS */
QFrame#TimelineHeader { background-color: #2b2b2b; border-right: 1px solid #444; }
QFrame#TrackControl { background-color: #262626; border-bottom: 1px solid #1a1a1a; min-height: 50px; }
QFrame#TimelineArea { background-color: #181818; }

/* TRANSPORT BUTTONS */
QPushButton[class="transport"] {
    background-color: transparent;
    border: none;
    color: #ddd;
    font-size: 18px; /* Bigger Icons */
    font-weight: bold;
}
QPushButton[class="transport"]:hover { color: #3997f3; }

/* DATA LISTS */
QTreeWidget { 
    background-color: #1b1b1b; 
    border: none; 
    color: #ccc; 
    font-size: 11px;
}
QHeaderView::section {
    background-color: #2a2a2a;
    color: #aaa;
    border: none;
    border-right: 1px solid #111;
    padding: 4px;
}
"""

class PremiereMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kanha Studio 2025 (Qt Pro)")
        self.resize(1600, 900)
        self.setStyleSheet(ADOBE_STYLESHEET)
        
        # 1. Configure Global Docking Behavior
        self.setDockOptions(QMainWindow.AllowNestedDocks | QMainWindow.AnimatedDocks)
        
        # Crucial: Set corner ownership so the Tool strip spans the full height
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)

        self.create_menus()
        self.init_ui_components()
        self.setup_default_layout() # <--- This fixes the "Messed Up" look

    def create_menus(self):
        bar = self.menuBar()
        bar.setStyleSheet("background-color: #1d1d1d; color: #ccc; font-size: 12px;")
        for m in ["File", "Edit", "Clip", "Sequence", "Markers", "Graphics", "View", "Window", "Help"]:
            bar.addMenu(m)

    def init_ui_components(self):
        # We store references to the docks so we can resize them later
        
        # 1. TOOLS (The thin strip on the left)
        self.dock_tools = QDockWidget("Tools", self)
        self.dock_tools.setFeatures(QDockWidget.NoDockWidgetFeatures) # Lock it in place usually
        self.dock_tools.setTitleBarWidget(QWidget()) # Completely hide title bar for cleaner look
        self.dock_tools.setFixedWidth(35)
        self.dock_tools.setWidget(self.create_tool_strip())
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_tools)

        # 2. PROJECT BIN
        self.dock_project = QDockWidget("Project: Kanha_Edit", self)
        self.dock_project.setWidget(self.create_project_bin())
        self.dock_project.setObjectName("DockProject")

        # 3. TIMELINE (The centerpiece)
        self.dock_timeline = QDockWidget("Sequence 01", self)
        self.dock_timeline.setWidget(self.create_complex_timeline())
        self.dock_timeline.setObjectName("DockTimeline")

        # 4. SOURCE MONITOR
        self.dock_source = QDockWidget("Source: (No Clip)", self)
        # Give it a black graphics view just like Program
        src_view = QGraphicsView()
        src_view.setStyleSheet("border: none; background: #000;")
        self.dock_source.setWidget(src_view)
        self.dock_source.setObjectName("DockSource")

        # 5. PROGRAM MONITOR
        self.dock_program = QDockWidget("Program: Sequence 01", self)
        self.dock_program.setWidget(self.create_program_monitor())
        self.dock_program.setObjectName("DockProgram")

        # Note: We DO NOT call addDockWidget here randomly.
        # We let setup_default_layout handle the placement.

    def setup_default_layout(self):
        """ 
        THE MAGIC SAUCE.
        This function forcibly arranges the windows into the standard NLE Grid.
        """
        # Clear State (if any)
        # Note: Qt builds layouts by 'splitting' existing docks.
        
        # Start by placing the Timeline at the bottom, occupying everything
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_timeline)
        
        # Split the Timeline: Put the Project Bin to the LEFT of the Timeline
        self.splitDockWidget(self.dock_timeline, self.dock_project, Qt.Horizontal)
        
        # Add the Program Monitor to the Top
        self.addDockWidget(Qt.TopDockWidgetArea, self.dock_program)
        
        # Split the Program Monitor: Put Source Monitor to the LEFT of Program
        self.splitDockWidget(self.dock_program, self.dock_source, Qt.Horizontal)

        # FORCE SIZES
        # Logic: width ratio lists. 
        # Top Row: [Source (40%), Program (60%)]
        self.resizeDocks([self.dock_source, self.dock_program], [600, 900], Qt.Horizontal)
        
        # Bottom Row: [Project (30%), Timeline (70%)]
        self.resizeDocks([self.dock_project, self.dock_timeline], [400, 1200], Qt.Horizontal)
        
        # Vertical Split: [Top (55%), Bottom (45%)]
        self.resizeDocks([self.dock_program, self.dock_timeline], [500, 400], Qt.Vertical)

    # --- WIDGET FACTORIES ---

    def create_program_monitor(self):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        # Graphic View
        view = QGraphicsView()
        view.setStyleSheet("background: black; border: none;")
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scene = QGraphicsScene()
        scene.setBackgroundBrush(QColor("#000"))
        view.setScene(scene)
        
        # Fake Video Box
        # We center a 16:9 rectangle
        scene.addRect(0,0, 1280, 720, pen=QPen(Qt.NoPen), brush=QColor(10,10,10))
        
        # The Blue Transformation Handle (Fake overlay)
        box_pen = QPen(QColor("#3997f3"))
        box_pen.setWidth(2)
        rect = scene.addRect(200, 100, 880, 520, pen=box_pen)
        
        layout.addWidget(view)
        
        # Controls
        controls = QFrame()
        controls.setStyleSheet("background: #1d1d1d; min-height: 40px; max-height: 40px; border-top: 1px solid #111;")
        h_layout = QHBoxLayout(controls)
        h_layout.setContentsMargins(10,0,10,0)
        
        tc = QLabel("00:01:02:10")
        tc.setStyleSheet("color: #3997f3; font-family: Consolas; font-size: 14px; font-weight: bold;")
        h_layout.addWidget(tc)
        
        h_layout.addStretch()
        
        btns = ["⏮", "⏪", "▶", "⏩", "⏭"]
        for t in btns:
            b = QPushButton(t)
            b.setProperty("class", "transport")
            b.setCursor(Qt.PointingHandCursor)
            h_layout.addWidget(b)
            
        h_layout.addStretch()
        
        # Cam/Settings icons
        snap = QPushButton("📷")
        snap.setProperty("class", "transport")
        h_layout.addWidget(snap)
        
        layout.addWidget(controls)
        return frame

    def create_project_bin(self):
        tree = QTreeWidget()
        tree.setHeaderLabels(["Name", "Frame Rate", "Media Duration", "Type"])
        tree.setAlternatingRowColors(True) # Stripes
        tree.setStyleSheet("alternate-background-color: #222;")
        
        data = [
            ("Interview_CamA_4K.mp4", "23.976", "00:14:02:05", "Movie"),
            ("Interview_CamB_4K.mp4", "23.976", "00:14:05:11", "Movie"),
            ("B-Roll_City.mov", "60.00", "00:00:45:00", "Movie"),
            ("Background_Music.wav", "48000 Hz", "00:03:12:00", "Audio"),
            ("Drone_Shot_01.mov", "59.94", "00:00:20:00", "Movie"),
        ]
        
        # Correct standard icon fetch
        icon = self.style().standardIcon(QStyle.SP_FileIcon)
        
        for row in data:
            item = QTreeWidgetItem(row)
            item.setIcon(0, icon)
            tree.addTopLevelItem(item)
            
        return tree

    def create_complex_timeline(self):
        # Main Container
        container = QFrame()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        # 1. Left Headers
        headers = QFrame()
        headers.setObjectName("TimelineHeader")
        headers.setFixedWidth(100)
        v_layout = QVBoxLayout(headers)
        v_layout.setContentsMargins(0,0,0,0)
        v_layout.setSpacing(1)
        
        track_names = ["V3", "V2", "V1", "", "A1", "A2", "A3"]
        colors = ["#888"]*3 + ["#000"] + ["#888"]*3 # Gap for visual separation
        
        for i, name in enumerate(track_names):
            row = QFrame()
            if name == "": 
                row.setStyleSheet("background: #222; max-height: 20px;") # Divider
            else:
                row.setObjectName("TrackControl")
                lbl = QLabel(name)
                lbl.setStyleSheet("color: #777; font-weight: bold; padding-left: 5px;")
                l = QVBoxLayout(row); l.addWidget(lbl); l.setAlignment(Qt.AlignVCenter)
            v_layout.addWidget(row)
            
        v_layout.addStretch()
        
        # 2. Right Tracks area
        tracks = QFrame()
        tracks.setObjectName("TimelineArea")
        tracks_layout = QVBoxLayout(tracks)
        # (In real implementation, this is a Custom Painted Widget, for now just a placeholder)
        lbl = QLabel("Sequences Go Here")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #444; font-size: 24px; font-weight: bold;")
        tracks_layout.addWidget(lbl)
        
        layout.addWidget(headers)
        layout.addWidget(tracks)
        
        return container

    def create_tool_strip(self):
        strip = QFrame()
        v = QVBoxLayout(strip)
        v.setContentsMargins(0,15,0,10)
        v.setSpacing(15)
        
        tools = ["⬉", "◫", "✄", "✎", "✋", "🔍"] 
        for t in tools:
            b = QPushButton(t)
            b.setFixedSize(35,35)
            b.setProperty("class", "transport")
            b.setStyleSheet("color: #aaa;") 
            v.addWidget(b)
            
        v.addStretch()
        return strip

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = PremiereMainWindow()
    window.show()
    
    sys.exit(app.exec())