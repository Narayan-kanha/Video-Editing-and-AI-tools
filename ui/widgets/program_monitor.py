from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QSlider, QPushButton
from PySide6.QtCore import Qt, QSize
from utils.asset_loader import AssetLoader
from utils import icons  # <--- IMPORT CONFIG

class ProgramMonitor(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.video_surface = QFrame()
        self.video_surface.setStyleSheet("background: black;")
        layout.addWidget(self.video_surface)
        
        controls = QFrame()
        controls.setStyleSheet("background: #1e1e1e; min-height: 40px;")
        h = QHBoxLayout(controls)
        h.setContentsMargins(10,5,10,5)
        
        self.lbl_time = QLabel("00:00:00:00")
        self.lbl_time.setStyleSheet("color: #3997f3; font-weight: bold; font-family: Consolas;")
        
        # --- USES CENTRAL CONFIG NOW ---
        self.btn_play = self.mk_btn(icons.PLAY)
        self.btn_back = self.mk_btn(icons.REWIND)
        self.btn_fwd  = self.mk_btn(icons.FORWARD)
        
        h.addWidget(self.lbl_time)
        h.addStretch()
        h.addWidget(self.btn_back)
        h.addWidget(self.btn_play)
        h.addWidget(self.btn_fwd)
        h.addStretch()
        
        layout.addWidget(controls)
        
        # Slider setup (kept standard)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        layout.addWidget(self.slider)

    def mk_btn(self, icon_var):
        btn = QPushButton()
        btn.setIcon(AssetLoader.icon(icon_var))
        btn.setIconSize(QSize(20,20))
        btn.setFixedSize(30,30)
        btn.setStyleSheet("border: none; background: transparent;")
        return btn

    def set_playing_state(self, is_playing):
        # Dynamically switch
        icon_name = icons.PAUSE if is_playing else icons.PLAY
        self.btn_play.setIcon(AssetLoader.icon(icon_name))