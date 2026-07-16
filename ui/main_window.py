from ui import custom_widgets as cw
from core import data_processor
import time

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
        
        self.left_layout = QtWidgets.QVBoxLayout()
        self.left_widget = QtWidgets.QWidget()
        self.left_widget.setLayout(self.left_layout)
        self.main_layout.addWidget(self.left_widget)

        self.visualizer = cw.VisualizerArea()
        self.left_layout.addWidget(self.visualizer)

        self.playback_control = cw.ScrubberBar(100)
        self.playback_control.playback_updated.connect(self._on_playback_update)
        self.left_layout.addWidget(self.playback_control)

        self.right_layout = QtWidgets.QVBoxLayout()
        self.right_widget = QtWidgets.QWidget()
        self.right_widget.setLayout(self.right_layout)
        self.main_layout.addWidget(self.right_widget)

        self.settings_menu = cw.SettingsWidget()
        self.settings_menu.scaling_method_updated.connect(self._on_scaling_method_update)
        self.settings_menu.scale_modifier_updated.connect(self._on_scale_modifier_update)
        self.settings_menu.craft_mesh_updated.connect(self._on_craft_mesh_update)
        self.right_layout.addWidget(self.settings_menu)

        self.drop_area = cw.FileDropArea()
        self.right_layout.addWidget(self.drop_area)

        self._datafile = None
        self.drop_area.file_dropped.connect(self._process_dropped_file)
    
    def _process_dropped_file(self, file_path: str) -> None:
        """Return a formatted DataFile processed from a dropped file.
        """
        self._datafile = data_processor.DataFile(file_path)
        self.playback_control.load_data(self._datafile)
    
    def _on_playback_update(self, new_time_index: float) -> None:
        """Updates the visualizer area to the new time index from the playback bar.
        """
        if self._datafile:
            new_vectors = self._datafile.get_vectors_at_index(new_time_index)
            self.visualizer.update_vector_display(new_vectors)
    
    def _on_scaling_method_update(self, new_scaling_method: str) -> None:
        """Updates the selected scaling method for the viualizer and redraws all vectors.
        """
        self.visualizer.selected_scaling_method = new_scaling_method
        self.visualizer.refresh_vector_display()

    def _on_scale_modifier_update(self, new_modifier: float) -> None:
        """Updates the selected scale modifier for the viualizer and redraws all vectors.
        """
        self.visualizer.selected_scale_modifier = new_modifier
        self.visualizer.refresh_vector_display()

    def _on_craft_mesh_update(self, new_craft_mesh: str) -> None:
        """Updates the seleced craft mesh for the visualizer and redraws the craft mesh.
        """
        self.visualizer.selected_craft_mesh = new_craft_mesh
        self.visualizer.draw_craft_model()