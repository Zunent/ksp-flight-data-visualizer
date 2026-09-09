import os
import sys

def get_resource_path(relative_path: str) -> str:
    """Resolve the absolute path to a resource, allowing for local development 
    and PyInstaller compiled bundles to be supported.
    """
    try:
        base_path: str = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path: str = os.path.abspath(".")

    return os.path.join(base_path, relative_path)