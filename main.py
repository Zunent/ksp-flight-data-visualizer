import os
import sys
import core.path_resolver
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase
from ui.main_window import MainWindow

if sys.platform.startswith("linux"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    font_id = QFontDatabase.addApplicationFont("assets/fonts/ChivoMono-Regular.ttf")

    stylesheet_path: str = core.path_resolver.get_resource_path("assets/stylesheets/navy_dark.qss")
    with open(stylesheet_path, "r", encoding="utf-8") as file:
        app.setStyleSheet(file.read())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())