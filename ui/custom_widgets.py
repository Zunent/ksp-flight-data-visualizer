import core
import core.data_processor
import os
import ui
import numpy as np
from typing import Any
from pathlib import Path

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QTimer, QElapsedTimer, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QIcon

import pyvista as pv
from pyvistaqt import QtInteractor

def create_horizontal_separator() -> QtWidgets.QFrame:
        """Returns a new horizontal bar.
        """
        bar = QtWidgets.QFrame()
        bar.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        bar.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        bar.setObjectName('horizontalBar')
        return bar

class FileDropArea(QtWidgets.QLabel):
    """A space on the interface for the user to drop in the data file for processing.
    """
    file_dropped = pyqtSignal(str)

    def __init__(self) -> None:
        """Initializes a FileDropArea widget.
        """
        super().__init__()
        
        self._default_text = 'Drag and drop a supported data file here.'
        self._valid_text = 'Drop data file for processing.'
        self._invalid_text = ('Invalid data type / too many files.\nAccepted file extensions are:\n' + 
                                ' | '.join(core.SUPPORTED_FILE_TYPES))

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        size_policy.setHeightForWidth(True)
        self.setSizePolicy(size_policy)

        self.setText(self._default_text)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)

        # For use on the style sheet.
        self.setObjectName('dataDropZone')
    
    def _update_style(self) -> None:
        """Forces Qt to redraw the widget when a state property changes.
        """
        self.style().unpolish(self)
        self.style().polish(self)

    def hasHeightForWidth(self) -> bool:
        """Indicates to the layout manager that this widget's height depends on its width.
        """
        return True

    def heightForWidth(self, a0: int) -> int:
        """Returns the preferred height for a given width to maintain a 1:1 square aspect ratio.
        """
        return round(a0 * (2/5))
    
    def dragEnterEvent(self, a0: QDragEnterEvent) -> None:
        """Triggered when user's cursor enters this widget's boundary while holding something.
        Checks if the cursor contains a file.
        """
        # Check if there is something being dragged and if it has a file path.
        # Also checks of web links, problem for future self.
        if a0.mimeData().hasUrls():
            urls = a0.mimeData().urls()
            is_valid = True

            # Ensure there is only one file being held.
            if len(urls) > 1:
                is_valid = False

            # Do checks on file extensions if they have been established.
            if is_valid and core.SUPPORTED_FILE_TYPES:
                file_path = urls[0].toLocalFile()
                _, extension = os.path.splitext(file_path)
                if extension.lower() not in core.SUPPORTED_FILE_TYPES:
                    is_valid = False
            
            if is_valid:
                self.setProperty('hover_state', 'valid')
                self.setText(self._valid_text)
                a0.acceptProposedAction()
            else:
                self.setProperty('hover_state', 'invalid')
                self.setText(self._invalid_text)
                a0.setDropAction(Qt.DropAction.IgnoreAction)
                a0.accept()
            
            self._update_style()
        else:
            a0.ignore()
    
    def dragLeaveEvent(self, a0: QDragLeaveEvent) -> None:
        """Triggered when user's cursor drags item away without dropping it.
        """
        self.setProperty('hover_state', 'none')
        self.setText(self._default_text)
        self._update_style()
    
    def dropEvent(self, a0: QDropEvent) -> None:
        """Trigerred when user drops item onto this widget.
        """
        if self.property('hover_state') == 'valid':
            file_paths = [url.toLocalFile() for url in a0.mimeData().urls()]
            
            # We have already ensured there is only one file in the event.
            first_file = file_paths[0]
            a0.acceptProposedAction()
            self.file_dropped.emit(first_file)
        else:
            a0.ignore()
        
        self.setProperty('hover_state', 'none')
        self.setText(self._default_text)
        self._update_style()

class VisualizerArea(QtWidgets.QWidget):
    """The 3D visualizer area for displaying vector data.

    Attributes:
    - selected_scaling_method: The selected method used to scale vectors.
    - selected_scale_modifier: The selected value used to multiply all vector lengths.
    - selected_craft_mesh: The name of the selected craft mesh.
    
    Private Attributes:
    - _main_mesh: The craft mesh currently displayed on the visualizer.
    - _drawn_actors: The actors that are currently displayed on the visualizer.
    - _craft_model: The mesh that has been drawn for the craft. None if not yet drawn.
    - _current_vectors: The vectors currently drawn to the visualizer.
    """
    selected_scaling_method: str
    selected_scale_modifier: float
    selected_craft_mesh: str

    _main_mesh: pv.DataObject | None
    _drawn_actors: list[Any]
    _craft_model: pv.Actor | None
    _current_vectors: list[core.data_processor.DataVector]

    def __init__(self) -> None:
        """Initializes the visualizer area.
        """
        super().__init__()

        self.selected_scaling_method = ui.DEFAULT_VECTOR_SCALING_METHOD
        self.selected_scale_modifier = ui.DEFAULT_OVERALL_SCALE
        self.selected_craft_mesh = ui.DEFAULT_CRAFT_MODEL
        
        self._main_mesh = None
        self._drawn_actors = []
        self._craft_model = None
        self._current_vectors = []

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.setMinimumHeight(600)

        self.plotter = QtInteractor()

        self.main_layout.addWidget(self.plotter.interactor)

        self.draw_craft_model()
        self.plotter.add_axes()
        self.plotter.set_background("white")
    
    def _draw_single_labeled_origin_vector(self, data_vector: core.data_processor.DataVector) -> None:
        """Draws an origin vector with a tip at <data_vector.data_value>, 
        a label with <data_vector.name> and the vector's value at the tip, and <data_vector.colour> as the colour.

        If the vector would have little to no length (tip lies on the origin), no vector will be drawn.
        If no colour has been defined, the vector will not be drawn.
        """
        vector_value, name, colour = data_vector.get_attributes()

        vector = np.array(vector_value)
        length = float(np.linalg.norm(vector))

        if length < ui.VECTOR_LENGTH_THRESHOLD or self.selected_scale_modifier == 0:
            return

        direction = vector / length

        # Add ability to process vector length so that longer and shorter vectors can be
        # viewed at the same time
        corrected_length = ui.VECTOR_SCALING_METHODS[self.selected_scaling_method](length) * self.selected_scale_modifier
        corrected_vector = direction * corrected_length

        # Because pyvista is stupid and just scales the entire arrow to the magnitute
        # of the vector, we must divide by length to get consistent arrows.
        actual_tip_length = min(ui.VECTOR_TIP_LENGTH / corrected_length, 1.0)
        actual_tip_radius = (0.1 * ui.VECTOR_THICKNESS) / corrected_length
        actual_shaft_radius = (0.05 * ui.VECTOR_THICKNESS) / corrected_length

        vector_arrow_mesh = pv.Arrow(
            start=(0, 0, 0),
            direction=direction,
            tip_length=actual_tip_length,
            tip_radius=actual_tip_radius,
            tip_resolution=ui.VECTOR_RESOLUTION,
            shaft_radius=actual_shaft_radius,
            shaft_resolution=ui.VECTOR_RESOLUTION,
            scale=corrected_length
        )

        if colour:
            rgb_colour = colour[0:3]
            alpha_value = colour[3] / 255.0 if len(colour) == 4 else 1.0

            arrow_actor = self.plotter.add_mesh(vector_arrow_mesh, 
                                                color=rgb_colour, 
                                                opacity=alpha_value,
                                                reset_camera=False, 
                                                render=False
                                                )
            self._drawn_actors.append(arrow_actor)

            label_actor = self.plotter.add_point_labels(
                corrected_vector,
                [(name + '\n' + str(data_vector))],
                italic=False,
                font_size=ui.LABEL_SIZE,
                text_color='black',
                always_visible=True,
                reset_camera=False,
                show_points=False,
                render=False
            )
            self._drawn_actors.append(label_actor)
    
    def _draw_labeled_origin_vectors(self, vectors: list[core.data_processor.DataVector]) -> None:
        """Draws a list of DataVectors to the visualizer area.
        """
        for current_vector in vectors:
            self._draw_single_labeled_origin_vector(current_vector)
    
    def _clear_drawn_actors(self) -> None:
        """Erases the actors that have been drawn and placed into <self._drawn_actors>.
        """
        for actor in self._drawn_actors:
            self.plotter.remove_actor(actor, render=False)
        
        self._drawn_actors.clear()
    
    def draw_craft_model(self) -> None:
        """Draws and refreshes the craft model at the origin.
        """
        if self._craft_model:
            self.plotter.remove_actor(self._craft_model, render=False)
        craft_model = self.selected_craft_mesh
        craft_mesh = pv.read('./assets/models/' + craft_model)
        self._craft_model = self.plotter.add_mesh(craft_mesh, style='wireframe', line_width=2, render=False)
        self.plotter.render()

    def update_vector_display(self, vectors: list[core.data_processor.DataVector]) -> None:
        """Erases all vectors already drawn on the display and replaces them with <vectors>.
        """
        self._clear_drawn_actors()
        self._current_vectors = vectors
        self._draw_labeled_origin_vectors(vectors)
        # Set to manually render all at once to eliminate flickering.
        self.plotter.render()

    def refresh_vector_display(self) -> None:
        """Erases all vectors already drawn and draws them again with updated values.
        For use if <self.selected_scaling_method> or <self.selected_scale_modifier> are updated.
        """
        self.update_vector_display(self._current_vectors)

    def update_craft_orientation(self, orientation: tuple[float, float, float]) -> None:
            """Updates the absolute rotation of the craft mesh.
            """
            if self._craft_model is None:
                return

            # Map the flight dynamics terms to 3D Cartesian axes.
            # Pitch = X, Yaw = Y, Roll = Z
            yaw, roll, pitch = orientation

            # (pitch yaw roll)
            # TODO Yaw, roll, and pitch are not properly set here. Figure out why. May be a problem on the data recorder side.
            self._craft_model.orientation = (pitch, yaw, roll)

            self.plotter.render()

class ScrubberBar(QtWidgets.QWidget):
    """A zone to control the playback and scrubbing of flight data visualization.

    Private Attributes:
    - _is_paused: Whether the data playback is paused.
    - _polling_interval: Polling interval for the async playback in ms.
    - _loaded_data: The DataFile the visualizer currently has loaded. None if no data has been loaded.
    - _time_indexes: List of indexes from self._loaded_data. Empty list if no data has been loaded.
    - _playback_index: Index of where the playback currently is in the DataFile.
    """
    _is_paused: bool
    _polling_interval: int
    _loaded_data: core.data_processor.DataFile | None
    _time_indexes: list[float]
    _playback_index: int

    playback_updated = pyqtSignal(float)

    def __init__(self, polling_interval: int) -> None:
        """Initializes a Scrubber Bar with a playback slider, rewind button, 
        play/pause button, and a position indicator.
        
        Sets playback polling interval to <polling_interval> ms.
        """
        super().__init__()
        self._polling_interval = polling_interval

        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        self.setObjectName("scrubberBar")

        self.setMinimumWidth(600)

        self.play_icon = QIcon("assets/icons/play.svg")
        self.pause_icon = QIcon("assets/icons/pause.svg")
        self.rewind_icon = QIcon("assets/icons/rewind.svg")

        # Rewind button to jump back to start of data playback.
        self.rewind_button = QtWidgets.QPushButton()
        self.rewind_button.setIcon(self.rewind_icon)
        self.rewind_button.pressed.connect(self._on_rewind_press)
        self.rewind_button.setObjectName("rewindButton")
        self.main_layout.addWidget(self.rewind_button)

        # Play button to begin regular playback of data.
        self.play_button = QtWidgets.QPushButton()
        self.play_button.setCheckable(True)
        self.play_button.setChecked(False)
        self.play_button.setIcon(self.play_icon)
        self.play_button.toggled.connect(self._on_toggle_pause)
        self.play_button.setObjectName("playButton")
        self.main_layout.addWidget(self.play_button)
        # Default is paused.
        self._is_paused = True

        # Slider for tracking playback progress and scrub through data.
        self.playback_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.playback_slider.setRange(0, 100)
        self.playback_slider.setValue(0)
        self._playback_index = 0
        self.playback_slider.valueChanged.connect(self._on_playback_location_update)
        self.playback_slider.sliderPressed.connect(self._on_playback_bar_pressed)
        self.playback_slider.sliderReleased.connect(self._on_playback_bar_released)
        self.playback_slider.setObjectName("playbackSlider")
        self.main_layout.addWidget(self.playback_slider)

        # Label to indicate data index.
        self.playback_position_indicator = QtWidgets.QLabel()
        self.playback_position_indicator.setText(f"t+{self.playback_slider.value()}s")
        self.playback_position_indicator.setObjectName("playbackPositionIndicator")
        self.main_layout.addWidget(self.playback_position_indicator)

        # No data loaded by default.
        self._loaded_data = None
        self._time_indexes = []

        # Setup the QTimer for polling
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_data)
        self.poll_timer.setInterval(self._polling_interval)
        
        # Setup a stopwatch to track real-world elapsed time
        self.elapsed_timer = QElapsedTimer()
        
        # Keeps track of where the playback time was when the user last paused
        self._playback_time_offset = 0.0

    def load_data(self, new_datafile: core.data_processor.DataFile) -> None:
        """Sets <self._loaded_data> to <new_datafile>.
        """
        self._loaded_data = new_datafile
        self._time_indexes = self._loaded_data.get_time_indexes()
        # Reset playback to the start.
        self._on_rewind_press()
        self.playback_slider.setRange(0, len(self._time_indexes) - 1)

    def _on_toggle_pause(self, is_checked: bool) -> None:
        """Triggered when the pause/play button is pressed.
        """
        if is_checked:
            self._try_unpause()
        else:
            self._try_pause()

    def _try_unpause(self) -> None:
        """Tries to set the play status to the unpaused state.
        Playback will not be unpaused if self._loaded_data is not a DataFile or self._time_indexes is empty.
        """
        if self._loaded_data and self._time_indexes:
            self._is_paused = False
            self.elapsed_timer.start()
            self.poll_timer.start()
            self.play_button.setIcon(self.pause_icon)
    
    def _try_pause(self) -> None:
        """Forces the play status to the paused state.
        """
        self._is_paused = True
        self.poll_timer.stop()
        self.play_button.setIcon(self.play_icon)
        if self._loaded_data and self._time_indexes:
            self._playback_time_offset = self._time_indexes[self._playback_index]
    
    def _on_rewind_press(self) -> None:
        """Triggered when the rewind button is pressed.
        """
        self.play_button.setChecked(False)
        self.playback_slider.setValue(0)
        self._playback_time_offset = self._time_indexes[0] if self._time_indexes else 0.0
        self._playback_index = 0
    
    def _on_playback_location_update(self, new_value: int) -> None:
        """Triggered when the playback slider's position is updated.
        """
        if not self._loaded_data:
            self.playback_position_indicator.setText(f"t+{new_value}s")
        else:
            self.playback_position_indicator.setText(f"t+{round(self._time_indexes[new_value], 1)}s")
            self.playback_updated.emit(self._time_indexes[new_value])
    
    def _on_playback_bar_pressed(self) -> None:
        """Triggered when the user starts moving the playback bar.
        """
        self.poll_timer.stop()

    def _on_playback_bar_released(self) -> None:
        """Triggered when the user releases the playback bar.
        """
        self._playback_index = self.playback_slider.value()

        if self._loaded_data and self._time_indexes:
            self._playback_time_offset = self._time_indexes[self._playback_index]
        if not self._is_paused:
            self._try_unpause()

    def _poll_data(self) -> None:
        """Runs every polling interval. Syncs the data index with real elapsed time.

        Preconditions:
         - self._loaded_data is not None
         - self._time_indexes is not None
        """
        current_playback_time = self._playback_time_offset + (self.elapsed_timer.elapsed() / 1000.0)
        index_changed = False
        while self._playback_index < len(self._time_indexes) - 1:
            next_timestamp = self._time_indexes[self._playback_index + 1]
            
            if current_playback_time >= next_timestamp:
                self._playback_index += 1
                index_changed = True
            else:
                break
        
        # Check if at the end of playback.
        if self._playback_index >= len(self._time_indexes) - 1:
            self.play_button.setChecked(False)
        
        # Update playback bar if needed.
        if index_changed:
            self.playback_slider.setValue(self._playback_index)

class SettingsWidget(QtWidgets.QWidget):
    """A zone for editing settings related to the playback of data.
    
    Private Attributes:
    - _craft_mesh_filenames: List of file names in assets/models, for use in communicating 
                    with the visualizer.
    - _scaling_methods: List of available scaling methods from ui/__init__, for use in
                    communicating with the visualizer.
    """
    _craft_mesh_filenames: list[str]
    _scaling_methods: list[str]

    scaling_method_updated = pyqtSignal(str)
    scale_modifier_updated = pyqtSignal(float)
    craft_mesh_updated = pyqtSignal(str)

    def __init__(self) -> None:
        """Initializes the settings widget.
        """
        super().__init__()

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        self.setObjectName("settingsArea")

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setSizePolicy(size_policy)

        main_layout.addWidget(create_horizontal_separator())

        scaling_method_label = QtWidgets.QLabel("Scaling Method")
        scaling_method_label.setObjectName("settingsLabel")
        self._scaling_methods = []
        self.scaling_method_dropdown = QtWidgets.QComboBox()
        self.scaling_method_dropdown.addItems(self._get_available_scaling_methods())
        self.scaling_method_dropdown.currentIndexChanged.connect(self._on_scaling_method_update)
        self.scaling_method_dropdown.setObjectName("settingsDropdown")
        main_layout.addWidget(scaling_method_label)
        main_layout.addWidget(self.scaling_method_dropdown)

        main_layout.addWidget(create_horizontal_separator())

        scale_modifier_label = QtWidgets.QLabel("Scale Modifier")
        scale_modifier_label.setObjectName("settingsLabel")
        main_layout.addWidget(scale_modifier_label)

        self.scale_modifier_spinbox = QtWidgets.QDoubleSpinBox()
        self.scale_modifier_spinbox.setMinimum(0)
        self.scale_modifier_spinbox.setValue(0.5)
        self.scale_modifier_spinbox.setSingleStep(0.1)
        self.scale_modifier_spinbox.valueChanged.connect(self._on_scale_modifier_update)
        self.scale_modifier_spinbox.setObjectName("settingsSpinbox")
        main_layout.addWidget(self.scale_modifier_spinbox)

        main_layout.addWidget(create_horizontal_separator())

        craft_mesh_label = QtWidgets.QLabel("Craft Mesh")
        craft_mesh_label.setObjectName("settingsLabel")
        self._craft_mesh_filenames = []
        self.craft_mesh_dropdown = QtWidgets.QComboBox()
        self.craft_mesh_dropdown.addItems(self._get_available_craft_meshes())
        self.craft_mesh_dropdown.currentIndexChanged.connect(self._on_craft_mesh_update)
        self.craft_mesh_dropdown.setObjectName("settingsDropdown")
        main_layout.addWidget(craft_mesh_label)
        main_layout.addWidget(self.craft_mesh_dropdown)

        main_layout.addWidget(create_horizontal_separator())
    
    def _get_available_scaling_methods(self) -> list[str]:
        """Returns a list of scaling methods available in <ui.VECTOR_SCALING_METHODS> formatted in title case.
        Sets <self._scaling_methods> to the original strings for the scaling methods.
        """
        self._scaling_methods = list(ui.VECTOR_SCALING_METHODS.keys())
        return [method.replace('_', ' ').title() for method in self._scaling_methods]
    
    def _get_available_craft_meshes(self) -> list[str]:
        """Returns a list of craft meshes available in assets/models formatted in title case. 
        Sets <self._craft_mesh_filenames> to the file names retrieved from assets/models.
        """
        models_path = Path(__file__).resolve().parent.parent / 'assets' / 'models'
        self._craft_mesh_filenames = [f.name for f in models_path.iterdir() if f.is_file()]
        return [mesh_name.split('.')[0].replace('-', ' ').title() for mesh_name in self._craft_mesh_filenames]
    
    def _on_scaling_method_update(self, new_index: int) -> None:
        """Handles a new scaling method being selected.
        """
        new_scaling_method = self._scaling_methods[new_index]
        self.scaling_method_updated.emit(new_scaling_method)

    def _on_scale_modifier_update(self, new_value: float) -> None:
        """Handles a new scale modifier being selected.
        """
        self.scale_modifier_updated.emit(new_value)

    def _on_craft_mesh_update(self, new_index: int) -> None:
        """Handles a new craft mesh being selected.
        """
        new_craft_name = self._craft_mesh_filenames[new_index]
        self.craft_mesh_updated.emit(new_craft_name)

class ValueDisplayWidget(QtWidgets.QWidget):
    """A widget for displaying values from the data file being played.
    
    Private Attributes:
    - _loaded_datafile: The data file that has been loaded. None if not loaded.
    - _variable_labels: A dict keying the variable labels currently displayed to their titles.
    """
    _loaded_datafile: core.data_processor.DataFile | None
    _variable_labels: dict[QtWidgets.QLabel, str]

    def __init__(self) -> None:
        """Initializes a value display widget.
        """
        super().__init__()

        self._loaded_datafile = None
        self._variable_labels = {}

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.setSizePolicy(size_policy)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.main_layout)

        self.main_label = QtWidgets.QLabel("No Data File Has Been Loaded")
        self.main_label.setObjectName("titleLabel")
        self.main_layout.addWidget(self.main_label, alignment=Qt.AlignmentFlag.AlignCenter)

    def _process_data_value(self, value: Any) -> Any:
        """Returns value rounded based on object type.
        """
        match value:
            case float():
                return round(value, ui.VALUE_DISPLAY_SINGLE_ROUND)
            case tuple():
                return tuple(round(x, ui.VALUE_DISPLAY_ORIENTATION_ROUND) 
                             for x in value)
            case _:
                return value

    def load_datafile(self, new_datafile: core.data_processor.DataFile) -> None:
        """Sets <self._loaded_datafile> to <new_datafile> and refreshes the displayed labels to
        the new variables.
        """
        if self._loaded_datafile is None:
            self.main_label.setText("Data Values")
            self.main_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.main_layout.setAlignment(Qt.AlignTop)
        
        self._loaded_datafile = new_datafile

        first_time_index = self._loaded_datafile.get_time_indexes()[0]
        new_values = self._loaded_datafile.get_values_at_index(first_time_index)
        label_titles = self._loaded_datafile.get_variable_labels()

        # Unload previous labels.
        for current_label in self._variable_labels.keys():
            self.main_layout.removeWidget(current_label)
        
        self._variable_labels.clear()

        # Check if there are any new values.
        if new_values is not None and label_titles:
            # Add in labels for the new datafile.
            for label_title in label_titles:
                new_label_value = self._process_data_value(new_values.loc[label_title])
                new_label = QtWidgets.QLabel(f"{label_title}: {new_label_value}")
                new_label.setObjectName("valueLabel")
                self.main_layout.addWidget(new_label)
                self._variable_labels[new_label] = label_title

    def update_value_labels(self, new_time_index: float) -> None:
        """Updates the displayed variable labels to the new time index using <self._loaded_datafile>.
        """
        new_values = self._loaded_datafile.get_values_at_index(new_time_index) if self._loaded_datafile else None

        # Check if there are any new values.
        if new_values is not None and self._variable_labels:
            # Add in labels for the new datafile.
            for label_widget, label_title in self._variable_labels.items():
                new_label_value = self._process_data_value(new_values.loc[label_title])
                label_widget.setText(f"{label_title}: {new_label_value}")