import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Required for QSettings to store data correctly on your PC
    app.setOrganizationName("KanhaStudios")
    app.setApplicationName("KanhaEditor")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())