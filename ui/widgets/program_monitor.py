from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                               QLabel, QSlider, QPushButton)
from PySide6.QtCore import Qt, QSize
# Import your new loader
from utils.asset_loader import AssetLoader 

class ProgramMonitor(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # 1. VIDEO SCREEN
        self.video_surface = QFrame()
        self.video_surface.setStyleSheet("background: black; border: 1px solid #000;")
        layout.addWidget(self.video_surface)
        
        # 2. CONTROLS BAR
        controls = QFrame()
        controls.setStyleSheet("background: #1e1e1e; min-height: 40px;")
        h_layout = QHBoxLayout(controls)
        h_layout.setContentsMargins(10, 5, 10, 5)
        
        # Timecode
        self.lbl_time = QLabel("00:00:00:00")
        self.lbl_time.setStyleSheet("color: #3997f3; font-weight: bold; font-family: Consolas;")
        
        # Buttons with Icons
        self.btn_play = self.create_icon_btn("play.png")
        self.btn_back = self.create_icon_btn("skip-back.png")
        self.btn_fwd  = self.create_icon_btn("fast-forward.png")
        
        h_layout.addWidget(self.lbl_time)
        h_layout.addStretch()
        h_layout.addWidget(self.btn_back)
        h_layout.addWidget(self.btn_play) # Toggle icon logic will be in Main
        h_layout.addWidget(self.btn_fwd)
        h_layout.addStretch()
        
        layout.addWidget(controls)
        
        # Scrubber
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #333; }
            QSlider::handle:horizontal { background: #3997f3; width: 14px; margin: -5px 0; border-radius: 7px; }
        """)
        layout.addWidget(self.slider)

    def create_icon_btn(self, icon_name):
        btn = QPushButton()
        btn.setIcon(AssetLoader.icon(icon_name))
        btn.setIconSize(QSize(20, 20))
        btn.setFixedSize(30, 30)
        btn.setStyleSheet("background: transparent; border: none;")
        return btn
        
    def set_playing_state(self, is_playing):
        # Swap Play/Pause icons
        if is_playing:
            self.btn_play.setIcon(AssetLoader.icon("pause.png"))
        else:
            self.btn_play.setIcon(AssetLoader.icon("play.png"))