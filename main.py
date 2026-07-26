import os
os.environ["QT_QPA_PLATFORM"] = "xcb"

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase
from ui.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    font_id = QFontDatabase.addApplicationFont("assets/fonts/ChivoMono-Regular.ttf")

    with open('stylesheet.qss', 'r') as f:
        app.setStyleSheet(f.read())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())