import core
import ui
import re
import math
import itertools

from pathlib import Path
import pandas as pd

class DataFile():
    """A class that processes and stores the data from a supported filetype.
    All vector data from an inputted spreadsheet is converted to DataVector classes.
    
    Attributes:
    - _file_path: The path to the relevant data file.
    - _sorted_labels: The data labels from an inputted spreadsheet sorted between
                    scalars and vectors.
    - _raw_dataframe: The dataframe directly converted from the input file.
    - _processed_dataframe: The dataframe containing data that has been processed 
                    into a format usable by the visualizer.
    - _comprehensive_label_to_colour: A dictionary that contains the colours to be used
                    in visualizing the vectors in the data file.
    """
    _file_path: Path
    _sorted_labels: dict[str, list[str]]
    _raw_dataframe: pd.DataFrame
    _processed_dataframe: pd.DataFrame
    _comprehensive_label_to_colour: dict[str, tuple[int, int, int, int]]

    def __init__(self, file_path: str) -> None:
        self._file_path = Path(file_path)
        self._raw_dataframe = self._process_valid_file()

        self._sorted_labels = {'scalars': [], 'vectors': [], 'orientation': []}
        self._filter_out_special_data()

        self._comprehensive_label_to_colour = ui.LABEL_TO_COLOUR.copy()
        self._processed_dataframe = self._create_empty_processed_dataframe()

        self._create_distinct_colours()
        self._process_raw_data()

    def _process_valid_file(self) -> pd.DataFrame:
        """Return a dataframe processed from <self._file_path> depending on the 
        file type.
        
        Preconditions:
        - self._file_path.suffix is in core.SUPPORTED_FILE_TYPES
        """
        match self._file_path.suffix:
            case '.csv':
                return pd.read_csv(self._file_path, index_col=0)
            case _:
                raise ValueError(f"Unsupported file type: {self._file_path.suffix}")

    def _filter_out_special_data(self) -> None:
        """Sets <self.sorted_labels> to be a dict of lists with keys 'scalars', 'vectors', and 'orientation' 
        each containing a list of names of data labels corresponding to scalar, vectors, or craft orientation
        if such data is present.
        """
        vector_pattern = re.compile(r'^([^XYZ]+)([XYZ])')
        data_labels = self._raw_dataframe.columns.to_list()
        label_holding = {}

        for label in data_labels:
            # Check if the label ends in X, Y, or Z.
            match = vector_pattern.match(label)
            if match:
                # Get the prefix and add it to a dict for tracking how many of them are found.
                prefix = match.group(1)
                label_holding[prefix] = 1 if prefix not in label_holding else label_holding[prefix] + 1
            else:
                self._sorted_labels['scalars'].append(label)
        
        for prefix, value in label_holding.items():
            # Checks if three vector-style labels have been found for a certain prefix.
            # This does not check if they are of X, Y, and Z.
            if value == 3:
                self._sorted_labels['vectors'].append(prefix)
            elif prefix not in self._sorted_labels['scalars']:
                self._sorted_labels['scalars'].append(prefix)
        
        orientation_labels = ['Pitch', 'Yaw', 'Roll']
        if all(label in self._sorted_labels['scalars'] for label in orientation_labels):
            # All orientation labels are present, remove them from scalars and add them to orientation.
            self._sorted_labels['orientation'] = orientation_labels
            for label in orientation_labels:
                self._sorted_labels['scalars'].remove(label)

    def _create_empty_processed_dataframe(self) -> pd.DataFrame:
        """Return an empty DataFrame with the indexes from <self._raw_dataframe> and
        the columns from <self._sorted_labels>.
        """
        column_labels = self._sorted_labels['scalars'] + self._sorted_labels['vectors']

        if self._sorted_labels['orientation']:
            column_labels.append('Orientation')
        
        return pd.DataFrame(index=self._raw_dataframe.index, columns=column_labels)

    def _create_distinct_colours(self) -> None:
        """Adds colours for vector labels without predetermined colours in ui.LABEL_TO_COLOUR
        into <self._comprehensive_label_to_colour>.
        
        Uses a process that tries to create colours that are as distinct as possible from existing colours.
        """
        vector_labels = self._sorted_labels['vectors'].copy()
        existing_coloured_labels = set(ui.LABEL_TO_COLOUR)

        vector_labels = [label.lower() for label in vector_labels if label.lower() not in existing_coloured_labels]

        def calculate_rgb_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
            """Calculates the straight-line Euclidean distance between two RGB colours."""
            return math.sqrt((c2[0] - c1[0])**2 + (c2[1] - c1[1])**2 + (c2[2] - c1[2])**2)
        
        for label in vector_labels:
            best_candidate = (0, 0, 0)
            max_min_distance = -1.0

            step_size = 32
            steps = list(range(0, 256, step_size))
            steps.append(255)

            for r, g, b in itertools.product(steps, steps, steps):
                candidate = (r, g, b)
                min_dist = min(calculate_rgb_distance(candidate, ex_col[0:3]) for 
                               ex_col in list(self._comprehensive_label_to_colour.values()))
                if min_dist > max_min_distance:
                    max_min_distance = min_dist
                    best_candidate = candidate
            
            # I would prefer to use tuple unpacking but pylance seems to not like that
            # and I really don't want to deal with it anymore.
            self._comprehensive_label_to_colour[label.lower()] = (best_candidate[0],
                                                                  best_candidate[1],
                                                                  best_candidate[2],
                                                                  core.DEFAULT_ALPHA
                                                                  )

    def _process_raw_data(self) -> None:
        """Processes the vectors from <self._raw_dataframe> into DataVectors and puts them 
        into <self._processed_dataframe> along with scalars.
        """
        for scalar_label in self._sorted_labels['scalars']:
            self._processed_dataframe[scalar_label] = self._raw_dataframe[scalar_label]
        
        if self._sorted_labels['orientation']:
            pitch_data = self._raw_dataframe['Pitch'].to_list()
            yaw_data = self._raw_dataframe['Yaw'].to_list()
            roll_data = self._raw_dataframe['Roll'].to_list()
            
            # Zip into a list of tuples: (pitch, yaw, roll)
            self._processed_dataframe['Orientation'] = list(zip(pitch_data, yaw_data, roll_data))

        for vector_label in self._sorted_labels['vectors']:
            x_data = self._raw_dataframe[vector_label + 'X'].to_list()
            y_data = self._raw_dataframe[vector_label + 'Y'].to_list()
            z_data = self._raw_dataframe[vector_label + 'Z'].to_list()

            combined_values = list(zip(x_data, y_data, z_data))
            compiled_datavectors = []

            for vector_value in combined_values:
                compiled_datavectors.append(DataVector(vector_value, 
                                                       vector_label, 
                                                       self._comprehensive_label_to_colour[vector_label.lower()]))
            
            self._processed_dataframe[vector_label] = compiled_datavectors

    def get_time_indexes(self) -> list[float]:
        """Returns a list of all indexes from <self._processed_dataframe>.
        """
        return self._processed_dataframe.index.tolist()

    def get_variable_labels(self) -> list[str]:
        """Returns a list of all variable labels from <self._processed_dataframe>.
        """
        return self._processed_dataframe.columns.tolist()
    
    def get_vectors_at_index(self, time_index: float) -> list[DataVector]:
        """Returns a list of vectors at row <time_index> of <self._processed_dataframe> if it is a valid index.
        Otherwise returns an empty list.
        """
        if time_index not in self._processed_dataframe.index:
            return []
        else:
            row_values = self._processed_dataframe.loc[time_index]
            filtered_vector_row_values = [x for x in row_values if isinstance(x, DataVector)]
            return filtered_vector_row_values
    
    def get_orientation_at_index(self, time_index: float) -> tuple[float, float, float] | None:
        """Returns the (Pitch, Yaw, Roll) tuple at the given time index. 
        Returns None if the index is invalid or if orientation data was not present.
        """
        if time_index not in self._processed_dataframe.index or not self._sorted_labels['orientation']:
            return None
        
        # oh huh you can just do that
        # you learn something new every day :>
        return self._processed_dataframe.at[time_index, 'Orientation'] # type: ignore

class DataVector():
    """A vector that contains label and colour information for displaying.
    An origin vector, so the tail is assumed to be at the origin.
    
    Attributes:
    - data_value: The location of the vector's tip.
    - label: The label to be used to represent the data.
    - colour: The colour of the vector expressed in 8-bit RGBA.
    """
    data_value: tuple[float, float, float]
    name: str
    colour: tuple[int, int, int, int] | None

    def __init__(self, data_value: tuple[float, float, float], 
                 name: str, colour: tuple[int, int, int, int] | None = None) -> None:
        """Initializes a DataVector class.
        If <name> is found in <ui.LABEL_TO_COLOUR>, <self.colour> is overriden with its value.
        """
        self.data_value = data_value
        self.name = name
        if colour in ui.LABEL_TO_COLOUR:
            self.colour = ui.LABEL_TO_COLOUR[colour]
        else:
            self.colour = colour

    def __str__(self) -> str:
        x, y, z = self.data_value
        return f"<{round(x, 2)}, {round(y, 2)}, {round(z, 2)}>"
    
    def update_value(self, new_value: tuple[float, float, float]) -> None:
        """Updates <self.data_value> to <new_value>.
        """
        self.data_value = new_value
    
    def get_attributes(self) -> tuple[tuple[float, float, float], 
                                      str, tuple[int, int, int, int] | None]:
        """Returns all the class' attributes in an organized tuple for easy unpacking.
        """
        return (self.data_value, self.name, self.colour)