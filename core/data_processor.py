import core
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