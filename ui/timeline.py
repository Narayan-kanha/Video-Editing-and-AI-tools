from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
import sys

# Try to import our custom Rust engine
try:
    import kanha_core # type: ignore
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    print("⚠️ Kanha Core (Rust) not found. Waveforms disabled.")

# --- WORKER THREAD (Keep GUI Smooth) ---
class WaveformWorker(QThread):
    finished = Signal(list)

    def __init__(self, file_path, width):
        super().__init__()
        self.path = file_path
        self.width = width

    def run(self):
        if not RUST_AVAILABLE:
            self.finished.emit([])
            return

        try:
            # CALLING RUST HERE
            # This is 100x faster than reading samples in Python
            data = kanha_core.get_waveform(self.path, self.width)
            self.finished.emit(data)
        except Exception as e:
            print(f"Rust Error: {e}")
            self.finished.emit([])

# --- THE WIDGET ---
class Timeline(QFrame):
    def __init__(self):
        super().__init__()
        # Visual styling for the background
        self.setStyleSheet("background-color: #1e1e1e; border-top: 1px solid #333;")
        self.waveform_data = []
        self.duration = 0
        
        # Placeholder Label
        self.lbl_info = QLabel("Drag Video Here / Import File")
        self.lbl_info.setStyleSheet("color: #444; font-size: 24px; font-weight: bold;")
        self.lbl_info.setAlignment(Qt.AlignCenter)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.lbl_info)

    def load_waveform(self, file_path):
        """ Start the Rust calculation in background """
        self.lbl_info.setText("Generating Waveform (Rust Engine)...")
        
        # We calculate 1 point per pixel of current width
        width = max(800, self.width()) 
        
        self.worker = WaveformWorker(file_path, width)
        self.worker.finished.connect(self.on_waveform_ready)
        self.worker.start()

    def on_waveform_ready(self, data):
        self.waveform_data = data
        if self.waveform_data:
            self.lbl_info.hide()
            self.update() # Triggers paintEvent

    def paintEvent(self, event):
        """ Draws the visual lines """
        if not self.waveform_data:
            return super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        mid_y = h / 2
        
        # Paint Logic
        pen = QPen(QColor("#3997f3")) # Adobe Blue
        pen.setWidth(1)
        painter.setPen(pen)

        # Draw the audio bars
        # Map our data array to current screen width
        data_len = len(self.waveform_data)
        
        for x in range(w):
            if x >= data_len: break
            
            # Retrieve Rust Data (0.0 to 1.0)
            amplitude = self.waveform_data[x] 
            
            # Scale height (e.g., 0.8 * total_height)
            bar_h = amplitude * h * 0.9 
            
            # Draw line centered vertically
            top = mid_y - (bar_h / 2)
            painter.drawLine(x, int(top), x, int(top + bar_h))