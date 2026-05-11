from ui import custom_widgets as cw

from PyQt5 import QtWidgets


class MainWindow(QtWidgets.QMainWindow):
    """The main window of the flight data visualizer.
    """

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Flight Data Visualizer")
        self.resize(1000, 600)

        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)

        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_widget.setLayout(self.main_layout)
        
        self.visualizer = cw.VisualizerArea()
        self.main_layout.addWidget(self.visualizer)

        self.drop_area = cw.FileDropArea()
        self.main_layout.addWidget(self.drop_area)