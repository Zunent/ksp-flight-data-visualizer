import os
import sys

if sys.platform.startswith("linux"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

def get_resource_path(relative_path: str) -> str:
    """Resolve the absolute path to a resource, allowing for local development 
    and PyInstaller compiled bundles to be supported.
    """
    try:
        base_path: str = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path: str = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase
from ui.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    font_id = QFontDatabase.addApplicationFont("assets/fonts/ChivoMono-Regular.ttf")

    stylesheet_path: str = get_resource_path("stylesheet.qss")
    with open(stylesheet_path, "r", encoding="utf-8") as file:
        app.setStyleSheet(file.read())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())