from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton
from PySide6.QtCore import QSize
from utils.asset_loader import AssetLoader 

class ToolStrip(QFrame):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(15)
        
        # Use your icon filenames here
        tools = [
            "mouse_pointer.png",  # Default arrow (assume you have one or make one)
            "code.png",           # Slice tool?
            "alert-triangle.png", # Hand tool?
            "file.png"            # Text tool?
        ]
        
        for icon_name in tools:
            btn = QPushButton()
            # If icon exists, use it. If not, use generic style
            btn.setIcon(AssetLoader.icon(icon_name))
            btn.setIconSize(QSize(24, 24))
            btn.setFixedSize(32, 32)
            btn.setStyleSheet("QPushButton { border: none; background: transparent; } QPushButton:hover { background: #333; border-radius: 5px; }")
            layout.addWidget(btn)
            
        layout.addStretch()