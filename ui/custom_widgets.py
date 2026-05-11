import core
import os
import pyvista as pv

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from pyvistaqt import QtInteractor

class FileDropArea(QtWidgets.QLabel):
    """A space on the interface for the user to drop in the data file for processing.
    """

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
        else:
            a0.ignore()
        
        self.setProperty('hover_state', 'none')
        self.setText(self._default_text)
        self._update_style()

class VisualizerArea(QtWidgets.QWidget):
    """The 3D visualizer area for displaying vector data.
    """
    
    def __init__(self) -> None:
        """Initializes the visualizer area.
        """
        super().__init__()
        
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.plotter = QtInteractor()

        self.main_layout.addWidget(self.plotter.interactor)

        self.plotter.add_axes()
        self.plotter.show_grid()
        self.plotter.set_background("white")