from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, 
                               QLabel, QSlider, QSpinBox, QFontComboBox, 
                               QPushButton, QColorDialog, QScrollArea, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class PropertiesPanel(QFrame):
    def __init__(self):
        super().__init__()
        
        # Make it scrollable because property lists get long
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: #1e1e1e; border: none;")
        
        # The container widget inside scroll area
        self.container = QWidget()
        self.container.setStyleSheet(".QWidget { background: transparent; }") # important for form layout
        self.form_layout = QVBoxLayout(self.container)
        self.form_layout.setContentsMargins(10, 10, 10, 10)
        self.form_layout.setSpacing(15)
        
        # --- SECTION 1: VIDEO TRANSFORM ---
        self.create_header("Motion")
        motion_form = QFormLayout()
        motion_form.setLabelAlignment(Qt.AlignLeft)
        
        self.sl_pos_x = self.create_property_slider("Position X", 960, 0, 3840)
        self.sl_pos_y = self.create_property_slider("Position Y", 540, 0, 2160)
        self.sl_scale = self.create_property_slider("Scale", 100, 0, 500)
        self.sl_rotation = self.create_property_slider("Rotation", 0, -360, 360)
        
        motion_form.addRow("Position X", self.sl_pos_x)
        motion_form.addRow("Position Y", self.sl_pos_y)
        motion_form.addRow("Scale", self.sl_scale)
        motion_form.addRow("Rotation", self.sl_rotation)
        
        self.form_layout.addLayout(motion_form)

        # --- SECTION 2: TEXT PROPERTIES ---
        self.create_separator()
        self.create_header("Text (Source Text)")
        text_form = QFormLayout()
        
        # Font Face Picker (Uses System Fonts)
        self.font_face = QFontComboBox()
        self.font_face.setStyleSheet("background: #333; color: #fff; border: 1px solid #555; padding: 2px;")
        
        # Font Style
        # (Usually FontComboBox handles basic styles, but specific bold/italic controls)
        
        # Font Size
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 200)
        self.font_size.setValue(48)
        self.font_size.setStyleSheet("background: #333; color: #fff; padding: 2px;")
        
        # Font Color Button
        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(50, 25)
        self.btn_color.setStyleSheet("background-color: #ffffff; border: 1px solid #555;")
        self.btn_color.clicked.connect(self.pick_color)
        
        text_form.addRow("Font", self.font_face)
        text_form.addRow("Size", self.font_size)
        text_form.addRow("Fill Color", self.btn_color)
        
        self.form_layout.addLayout(text_form)
        
        # Spacer at bottom
        self.form_layout.addStretch()
        
        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)

    def create_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #ddd; font-weight: bold; font-size: 13px; margin-bottom: 5px;")
        self.form_layout.addWidget(lbl)

    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background: #444; max-height: 1px; margin: 10px 0;")
        self.form_layout.addWidget(line)

    def create_property_slider(self, tooltip, val, min_v, max_v):
        # We could combine a QSlider + QSpinBox here for advanced control
        # keeping it simple QSlider for now
        sl = QSlider(Qt.Horizontal)
        sl.setRange(min_v, max_v)
        sl.setValue(val)
        sl.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #333; }
            QSlider::handle:horizontal { background: #3997f3; width: 12px; margin: -4px 0; border-radius: 6px; }
        """)
        return sl

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.btn_color.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")