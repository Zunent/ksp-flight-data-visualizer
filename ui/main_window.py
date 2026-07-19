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
        self.main_layout.addWidget(self.left_widget, stretch=7)

        self.visualizer = cw.VisualizerArea()
        self.left_layout.addWidget(self.visualizer)

        self.playback_control = cw.ScrubberBar(100)
        self.playback_control.playback_updated.connect(self._on_playback_update)
        self.left_layout.addWidget(self.playback_control)

        # Set up dynamic scroll bar on right side (scroll bar appears and disappears as needed)
        self.right_widget = QtWidgets.QScrollArea()
        self.right_widget.setWidgetResizable(True)
        self.right_widget.setMinimumWidth(450)
        self.right_widget.setMaximumWidth(600)

        self.right_content_widget = QtWidgets.QWidget()
        self.right_layout = QtWidgets.QVBoxLayout()
        self.right_content_widget.setLayout(self.right_layout)

        self.right_widget.setWidget(self.right_content_widget)
        self.main_layout.addWidget(self.right_widget, stretch=3)

        self.value_display = cw.ValueDisplayWidget()
        self.right_layout.addWidget(self.value_display)

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
        self.value_display.load_datafile(self._datafile)
    
    def _on_playback_update(self, new_time_index: float) -> None:
        """Updates the visualizer area to the new time index from the playback bar.
        """
        if self._datafile:
            new_vectors = self._datafile.get_vectors_at_index(new_time_index)
            self.visualizer.update_vector_display(new_vectors)

            self.value_display.update_value_labels(new_time_index)

            new_orientation = self._datafile.get_orientation_at_index(new_time_index)
            if new_orientation:
                self.visualizer.update_craft_orientation(new_orientation)
    
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