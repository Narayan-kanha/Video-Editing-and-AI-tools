# ui/widgets/project_bin.py
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication, QStyle

class ProjectBin(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Name", "Details", "Type"])
        self.setAlternatingRowColors(True)
        self.setStyleSheet("alternate-background-color: #222;")
        
    def add_item(self, name, details, file_path):
        item = QTreeWidgetItem([name, details, "Movie"])
        # Save the actual path in hidden data so we can play it later
        item.setData(0, 32, file_path) # 32 is Qt.UserRole
        
        # Standard Icon
        icon = QApplication.style().standardIcon(QStyle.SP_FileIcon)
        item.setIcon(0, icon)
        
        self.addTopLevelItem(item)