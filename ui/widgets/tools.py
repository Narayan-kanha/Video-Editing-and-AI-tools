# ui/widgets/tools.py
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton

class ToolStrip(QFrame):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,10,0,10)
        
        tools = ["⬉", "◫", "✄", "✎", "✋", "🔍"]
        for icon in tools:
            btn = QPushButton(icon)
            btn.setFixedSize(30,30)
            btn.setProperty("class", "transport")
            # Specific override for tool styling
            btn.setStyleSheet("font-size: 16px; color: #aaa;")
            layout.addWidget(btn)
            
        layout.addStretch()