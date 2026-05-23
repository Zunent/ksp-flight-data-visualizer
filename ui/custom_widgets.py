import core
import core.data_processor
import os
import ui
import numpy as np
from typing import Any

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
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

    Attributes:
    - _main_mesh: The craft mesh currently displayed on the visualizer.
    - _drawn_vectors: The vectors that are currently displayed on the visualizer.
    """
    _main_mesh: pv.DataObject | None
    _drawn_vectors: list[Any]

    def __init__(self) -> None:
        """Initializes the visualizer area.
        """
        super().__init__()
        
        self._main_mesh = None
        self._drawn_vectors = []

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.plotter = QtInteractor()

        self.main_layout.addWidget(self.plotter.interactor)

        self.plotter.add_axes()
        self.plotter.set_background("white")
    
    def _draw_single_labeled_origin_vector(self, data_vector: core.data_processor.DataVector) -> None:
        """Draws an origin vector with a tip at <data_vector.data_value>, 
        a label with <data_vector.name> and the vector's value at the tip, and <data_vector.colour> as the colour.

        If the vector would have no length (tip lies on the origin), no vector will be drawn.
        If no colour has been defined, the vector will not be drawn.
        """
        vector_value, name, colour = data_vector.get_attributes()
        if vector_value == (0, 0, 0):
            return

        vector = np.array(vector_value)
        length = float(np.linalg.norm(vector))

        direction = vector / length

        vector_arrow_mesh = pv.Arrow(
            start=(0, 0, 0),
            direction=direction,
            tip_length=ui.VECTOR_TIP_LENGTH,
            tip_radius=(0.1 * ui.VECTOR_THICKNESS),
            tip_resolution=ui.VECTOR_RESOLUTION,
            shaft_radius=(0.05 * ui.VECTOR_THICKNESS),
            shaft_resolution=ui.VECTOR_RESOLUTION,
            scale=length
        )

        if colour:
            self._drawn_vectors.append(self.plotter.add_mesh(vector_arrow_mesh, color=colour))
            self.plotter.add_point_labels(
                vector_value,
                [(name + '\n' + str(vector_value).replace('(', '<').replace(')', '>'))],
                italic=False,
                font_size=ui.LABEL_SIZE,
                text_color='black',
                always_visible=True
            )
    
    def _draw_labeled_origin_vectors(self, vectors: list[core.data_processor.DataVector]) -> None:
        """Draws a list of DataVectors to the visualizer area.
        """
        for current_vector in vectors:
            self._draw_single_labeled_origin_vector(current_vector)
    
    def _clear_drawn_vectors(self) -> None:
        """Erases the vectors that have been drawn and placed into <self._drawn_vectors>.
        """
        for actor in self._drawn_vectors:
            self.plotter.remove_actor(actor)
        
        self._drawn_vectors.clear()
        self.plotter.clear_point_labels()
    
    def update_vector_display(self, vectors: list[core.data_processor.DataVector]) -> None:
        """Erases all vectors already drawn on the display and replaces them with <vectors>.
        """
        self._clear_drawn_vectors()
        self._draw_labeled_origin_vectors(vectors)