from PySide6.QtWidgets import (QFrame, QVBoxLayout, QTreeWidget, 
                               QTreeWidgetItem, QLineEdit)
from PySide6.QtCore import Qt

class EffectsPanel(QFrame):
    def __init__(self):
        super().__init__()
        
        # --- UI LAYOUT ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 1. Search Bar (like Premiere's bin)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Effects...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background: #2b2b2b;
                color: #ddd;
                border: 1px solid #444;
                padding: 4px;
                border-radius: 3px;
                font-family: 'Segoe UI';
            }
            QLineEdit:focus {
                border: 1px solid #3997f3;
            }
        """)
        self.search_bar.textChanged.connect(self.filter_effects)
        layout.addWidget(self.search_bar)

        # 2. Effects Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(15)
        self.tree.setAnimated(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: #1b1b1b;
                color: #ccc;
                border: none;
                font-family: 'Segoe UI';
                font-size: 11px;
            }
            QTreeWidget::item:hover {
                background: #333;
            }
            QTreeWidget::item:selected {
                background: #444;
                color: white;
            }
        """)
        layout.addWidget(self.tree)
        
        # Populate Mock Data
        self.populate_effects()

    def populate_effects(self):
        """ Hardcoded industry standard categories """
        data = {
            "Audio Effects": ["Amplitude", "Delay", "Echo", "Reverb", "Parametric EQ"],
            "Audio Transitions": ["Constant Power", "Exponential Fade"],
            "Video Effects": ["Blur & Sharpen", "Color Correction", "Distort", "Generate", "Transform"],
            "Video Transitions": ["Dissolve", "Iris", "Page Peel", "Slide", "Zoom", "Wipe"]
        }
        
        for category, items in data.items():
            parent = QTreeWidgetItem([category])
            parent.setExpanded(True) # Expand folders by default
            # Give folders a different look/color?
            # parent.setForeground(0, QBrush(QColor("#ddd"))) 
            
            for item_name in items:
                child = QTreeWidgetItem([item_name])
                parent.addChild(child)
            
            self.tree.addTopLevelItem(parent)

    def filter_effects(self, text):
        """ Basic search filtering logic """
        search_term = text.lower()
        
        # Loop all Top Categories
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            category = root.child(i)
            hide_category = True
            
            # Loop children
            for j in range(category.childCount()):
                effect = category.child(j)
                eff_text = effect.text(0).lower()
                
                if search_term in eff_text:
                    effect.setHidden(False)
                    hide_category = False # If one child matches, show category
                else:
                    effect.setHidden(True)
            
            category.setHidden(hide_category)