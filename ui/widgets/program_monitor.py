# ui/widgets/program_monitor.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QSlider, QPushButton
from PySide6.QtCore import Qt

class ProgramMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        # 1. VIDEO SURFACE (Public variable, Logic needs this)
        self.video_surface = QFrame()
        self.video_surface.setStyleSheet("background-color: black; border: 1px solid #111;")
        layout.addWidget(self.video_surface)
        
        # 2. CONTROLS
        controls = QFrame()
        controls.setObjectName("TransportBar")
        h_layout = QHBoxLayout(controls)
        h_layout.setContentsMargins(10,0,10,0)
        
        # Elements
        self.lbl_time = QLabel("00:00:00:00")
        self.lbl_time.setStyleSheet("color: #3997f3; font-family: Consolas; font-weight: bold;")
        
        # Buttons (Public access for Logic)
        self.btn_rewind = QPushButton("⏪")
        self.btn_play = QPushButton("▶")
        self.btn_ff = QPushButton("⏩")
        
        for b in [self.btn_rewind, self.btn_play, self.btn_ff]:
            b.setProperty("class", "transport")
            
        h_layout.addWidget(self.lbl_time)
        h_layout.addStretch()
        h_layout.addWidget(self.btn_rewind)
        h_layout.addWidget(self.btn_play)
        h_layout.addWidget(self.btn_ff)
        h_layout.addStretch()
        
        # Scrubber
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        
        layout.addWidget(self.slider)
        layout.addWidget(controls)