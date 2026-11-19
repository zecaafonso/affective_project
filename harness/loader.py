import importlib
import os
import sys


def load_engine(project_dir):
    """Import engine/engine.py of a project folder and return an Engine instance."""
    project_dir = os.path.abspath(project_dir)
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)
    module = importlib.import_module("engine.engine")
    return module.Engine()
