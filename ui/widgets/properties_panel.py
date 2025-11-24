from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel, QSlider, 
                               QSpinBox, QFontComboBox, QPushButton, QColorDialog, 
                               QScrollArea, QFrame, QHBoxLayout)
from PySide6.QtCore import Qt, QSize
from utils.asset_loader import AssetLoader
from utils import icons # Central Config

class PropertiesPanel(QFrame):
    def __init__(self):
        super().__init__()
        
        # Scroll Setup
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: #1e1e1e; border: none;")
        
        container = QWidget()
        self.vbox = QVBoxLayout(container)
        self.vbox.setSpacing(20) # Spacing between groups
        self.vbox.setContentsMargins(10, 10, 10, 10)
        
        # --- 1. MOTION SECTION (With "<>" Icon) ---
        self.create_group(icons.PROP_MOTION, "Motion")
        
        motion_form = QFormLayout()
        motion_form.setLabelAlignment(Qt.AlignLeft)
        
        self.sl_pos_x = self.create_slider("Position X", 960, 0, 3840)
        self.sl_pos_y = self.create_slider("Position Y", 540, 0, 2160)
        self.sl_scale = self.create_slider("Scale", 100, 0, 500)
        self.sl_rotation = self.create_slider("Rotation", 0, -360, 360)

        motion_form.addRow("Position X", self.sl_pos_x)
        motion_form.addRow("Position Y", self.sl_pos_y)
        motion_form.addRow("Scale", self.sl_scale)
        motion_form.addRow("Rotation", self.sl_rotation)
        
        # Add the form to our group
        self.current_group_layout.addLayout(motion_form)

        # --- 2. TEXT SECTION (With "File" Icon) ---
        self.create_group(icons.PROP_TEXT, "Text (Source Text)")
        
        text_form = QFormLayout()
        self.font_face = QFontComboBox()
        self.font_face.setStyleSheet("background: #333; color: #fff; padding: 4px;")
        
        self.font_size = QSpinBox()
        self.font_size.setRange(10, 200)
        self.font_size.setValue(40)
        self.font_size.setStyleSheet("background: #333; color: #fff;")
        
        text_form.addRow("Font", self.font_face)
        text_form.addRow("Size", self.font_size)
        
        self.current_group_layout.addLayout(text_form)

        self.vbox.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def create_group(self, icon_name, title_text):
        """ Custom UI to match your screenshot layout """
        # Wrapper
        group_frame = QWidget()
        g_layout = QHBoxLayout(group_frame)
        g_layout.setContentsMargins(0,0,0,0)
        g_layout.setAlignment(Qt.AlignTop)
        
        # A. The Icon (Left Sidebar)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(AssetLoader.icon(icon_name).pixmap(24, 24))
        icon_lbl.setStyleSheet("padding-top: 0px;") # Align with title
        icon_lbl.setAlignment(Qt.AlignTop)
        
        # B. The Content Area
        content_col = QWidget()
        c_layout = QVBoxLayout(content_col)
        c_layout.setContentsMargins(0,0,0,0)
        
        # Title
        lbl_title = QLabel(title_text)
        lbl_title.setStyleSheet("color: #ddd; font-weight: bold; font-size: 14px; margin-bottom: 8px;")
        
        c_layout.addWidget(lbl_title)
        
        # Prepare content area for fields
        self.current_group_layout = c_layout 
        
        g_layout.addWidget(icon_lbl)     # Add Icon Left
        g_layout.addWidget(content_col, 1) # Add Content Right
        
        self.vbox.addWidget(group_frame)

    def create_slider(self, tooltip, val, min_v, max_v):
        sl = QSlider(Qt.Horizontal)
        sl.setRange(min_v, max_v)
        sl.setValue(val)
        return sl