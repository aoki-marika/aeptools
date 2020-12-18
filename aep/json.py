import json
from io import BufferedReader, BufferedWriter
from pathlib import Path
from .aep import Project, Texture

class JsonDecoder(object):
    def __init__(self) -> None:
        return

    def decode(self, input_path: Path) -> Project:
        return None

class JsonEncoder(object):
    def __init__(self) -> None:
        return

    def encode(self, project: Project, output_path: Path) -> None:
        return