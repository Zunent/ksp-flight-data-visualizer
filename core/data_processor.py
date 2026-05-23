import core
import ui
import re

def filter_out_vectors(data_labels: list[str]) -> dict[str, list[str | None]]:
    """Returns a dict of lists with keys 'scalars' and 'vectors', each containing a list
    of names of data labels corresponding to scalars or vectors.
    """
    sorted_labels = {'scalars': [], 'vectors': []}
    vector_pattern = re.compile(r'^([^XYZ]+)([XYZ])')

    label_holding = {}
    for label in data_labels:
        match = vector_pattern.match(label)
        if match:
            prefix, marker = match.group(1), match.group(2)
            label_holding[prefix] = 1 if prefix not in label_holding else label_holding[prefix] + 1
        else:
            sorted_labels['scalars'].append(label)
    
    for prefix, value in label_holding.items():
        if value == 3:
            sorted_labels['vectors'].append(prefix)
    
    print(sorted_labels)
    return sorted_labels


class DataVector():
    """A vector that contains label and colour information for displaying.
    An origin vector, so the tail is assumed to be at the origin.
    
    Attributes:
    - data_value: The location of the vector's tip.
    - label: The label to be used to represent the data.
    - colour: The colour of the vector expressed in 8-bit RGB.
    """
    data_value: tuple[float, float, float]
    name: str
    colour: tuple[int, int, int] | None

    def __init__(self, data_value: tuple[float, float, float], 
                 name: str, colour: tuple[int, int, int] | None = None) -> None:
        """Initializes a DataVector class.
        If <name> is found in <ui.LABEL_TO_COLOUR>, <self.colour> is overriden with its value.
        """
        self.data_value = data_value
        self.name = name
        if colour in ui.LABEL_TO_COLOUR:
            self.colour = ui.LABEL_TO_COLOUR[colour]
        else:
            self.colour = colour
    
    def update_value(self, new_value: tuple[float, float, float]) -> None:
        """Updates <self.data_value> to <new_value>.
        """
        self.data_value = new_value
    
    def get_attributes(self) -> tuple[tuple[float, float, float], 
                                      str, tuple[int, int, int] | None]:
        """Returns all the class' attributes in an organized tuple for easy unpacking.
        """
        return (self.data_value, self.name, self.colour)