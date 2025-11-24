# ui/widgets/timeline.py
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class Timeline(QFrame):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        # HEADERS
        headers = QFrame()
        headers.setObjectName("TimelineHeader")
        headers.setFixedWidth(100)
        v_layout = QVBoxLayout(headers)
        v_layout.setSpacing(1)
        v_layout.setContentsMargins(0,0,0,0)
        
        # Create Fake Tracks
        track_names = ["V3", "V2", "V1", "", "A1", "A2", "A3"]
        for name in track_names:
            row = QFrame()
            if name: 
                row.setObjectName("TrackControl")
                lbl = QLabel(name)
                lbl.setStyleSheet("color: #777; padding-left: 5px; font-weight: bold;")
                box = QVBoxLayout(row); box.addWidget(lbl); box.setAlignment(Qt.AlignVCenter)
            else:
                row.setStyleSheet("background: #222; max-height: 20px;") # Divider
            v_layout.addWidget(row)
        v_layout.addStretch()
        
        # CLIP AREA (Placeholder for now)
        tracks = QFrame()
        tracks.setStyleSheet("background: #181818;")
        # Center label placeholder
        ctr = QVBoxLayout(tracks)
        lbl = QLabel("Sequences Go Here")
        lbl.setStyleSheet("color: #333; font-size: 30px; font-weight: bold;")
        lbl.setAlignment(Qt.AlignCenter)
        ctr.addWidget(lbl)
        
        layout.addWidget(headers)
        layout.addWidget(tracks)