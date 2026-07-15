import core
import core.data_processor
import os
import ui
import numpy as np
from typing import Any

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QTimer, QElapsedTimer, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent

import pyvista as pv
from pyvistaqt import QtInteractor

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
        self._invalid_text = ('Invalid data type / too many files. Accepted file extensions are:\n' + 
                                ' | '.join(core.SUPPORTED_FILE_TYPES))

        self.setText(self._default_text)
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)

        # For use on the style sheet.
        self.setObjectName('dataDropZone')
    
    def _update_style(self) -> None:
        """Forces Qt to redraw the widget when a state property changes.
        """
        self.style().unpolish(self)
        self.style().polish(self)
    
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

    Private Attributes:
    - _main_mesh: The craft mesh currently displayed on the visualizer.
    - _drawn_actors: The actors that are currently displayed on the visualizer.
    """
    _main_mesh: pv.DataObject | None
    _drawn_actors: list[Any]

    def __init__(self) -> None:
        """Initializes the visualizer area.
        """
        super().__init__()
        
        self._main_mesh = None
        self._drawn_actors = []

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.plotter = QtInteractor()

        self.main_layout.addWidget(self.plotter.interactor)

        self._draw_craft_model()
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

        if length < ui.VECTOR_LENGTH_THRESHOLD:
            return

        direction = vector / length

        # Add ability to process vector length so that longer and shorter vectors can be
        # viewed at the same time
        corrected_length = ui.VECTOR_SCALING_METHODS[ui.SELECTED_VECTOR_SCALING_METHOD](length) * ui.OVERALL_SCALE

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
            arrow_actor = self.plotter.add_mesh(vector_arrow_mesh, color=colour, reset_camera=False, render=False)
            self._drawn_actors.append(arrow_actor)

            label_actor = self.plotter.add_point_labels(
                vector_value,
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
    
    def _draw_craft_model(self) -> None:
        """Draws the craft model at the origin.
        """
        craft_model = ui.SELECTED_CRAFT_MODEL
        craft_mesh = pv.read('./assets/models/' + craft_model + '.stl')
        self._craft_model = self.plotter.add_mesh(craft_mesh, style='wireframe', line_width=2)

    def update_vector_display(self, vectors: list[core.data_processor.DataVector]) -> None:
        """Erases all vectors already drawn on the display and replaces them with <vectors>.
        """
        self._clear_drawn_actors()
        self._draw_labeled_origin_vectors(vectors)
        # Set to manually render all at once to eliminate flickering.
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

        # Rewind button to jump back to start of data playback.
        self.rewind_button = QtWidgets.QPushButton()
        self.rewind_button.pressed.connect(self._on_rewind_press)
        self.main_layout.addWidget(self.rewind_button)

        # Play button to begin regular playback of data.
        self.play_button = QtWidgets.QPushButton()
        self.play_button.setCheckable(True)
        self.play_button.setChecked(False)
        self.play_button.toggled.connect(self._on_toggle_pause)
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
        self.main_layout.addWidget(self.playback_slider)

        # Label to indicate data index.
        self.playback_position_indicator = QtWidgets.QLabel()
        self.playback_position_indicator.setText(str(self.playback_slider.value()))
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
    
    def _try_pause(self) -> None:
        """Forces the play status to the paused state.
        """
        self._is_paused = True
        self.poll_timer.stop()
        if self._loaded_data and self._time_indexes:
            self._playback_time_offset = self._time_indexes[self._playback_index]
    
    def _on_rewind_press(self) -> None:
        """Triggered when the rewind button is pressed.
        """
        self.play_button.setChecked(False)
        self.playback_slider.setValue(0)
        self._playback_time_offset = 0.0
        self._playback_index = 0
    
    def _on_playback_location_update(self, new_value: int) -> None:
        """Triggered when the playback slider's position is updated.
        """
        if not self._loaded_data:
            self.playback_position_indicator.setText(str(new_value))
        else:
            self.playback_position_indicator.setText(str(round(self._time_indexes[new_value], 1)))
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