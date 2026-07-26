import numpy as np

# Parameters for all drawn vectors.
VECTOR_THICKNESS = 0.5
VECTOR_RESOLUTION = 10
VECTOR_TIP_LENGTH = 0.1
VECTOR_LENGTH_THRESHOLD = 0.01

VECTOR_SCALING_METHODS = {
    "linear": lambda x: x,
    "logarithmic": lambda x: np.log(x + 1),
    "square_root": lambda x: np.sqrt(x) 
}

DEFAULT_VECTOR_SCALING_METHOD = "linear"
DEFAULT_OVERALL_SCALE = 0.5

# Parameter(s) for all labels.
LABEL_SIZE = 20

LABEL_TO_COLOUR = {
    'aero': (129, 181, 230, 150),
    'dot': (230, 198, 71, 150),
    'thrust': (109, 39, 214, 150)
}

DEFAULT_CRAFT_MODEL = 'diamond-1.stl'

VALUE_DISPLAY_SINGLE_ROUND = 2
VALUE_DISPLAY_ORIENTATION_ROUND = 1