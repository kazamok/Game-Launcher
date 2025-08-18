import sys
import os
from pathlib import Path

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        # If not bundled, use the project's root directory
        base_path = Path(__file__).parent.parent.parent
    
    return base_path / relative_path
