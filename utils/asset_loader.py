import os
import sys
from PySide6.QtGui import QIcon, QPixmap

class AssetLoader:
    """ Helps load images from the 'assets' folder safely """
    
    @staticmethod
    def get_path(filename):
        # Base dir is where main.py is
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "assets", filename)

    @staticmethod
    def icon(filename):
        path = AssetLoader.get_path(filename)
        if os.path.exists(path):
            return QIcon(path)
        return QIcon() # Empty icon fallback