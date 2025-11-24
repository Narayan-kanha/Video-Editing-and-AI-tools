import os
from PySide6.QtGui import QIcon, QPixmap
# Import the config we just made
from . import icons 

class AssetLoader:
    
    @staticmethod
    def get_path(filename):
        """ Resolves the full path to an asset file """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Security check: ensures filename isn't empty
        if not filename: return ""
        return os.path.join(base_dir, "assets", filename)

    @staticmethod
    def icon(filename):
        """ Returns QIcon, safe fallback if file missing """
        path = AssetLoader.get_path(filename)
        if os.path.exists(path):
            return QIcon(path)
        # Optional: Print warning so you know an image is missing
        # print(f"⚠️ Warning: Missing Icon {filename}")
        return QIcon()