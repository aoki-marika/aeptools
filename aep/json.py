from io import BufferedReader, BufferedWriter
from .aep import Project

class JsonDecoder(object):
    def __init__(self) -> None:
        return

    def decode(self, input_file: BufferedReader) -> Project:
        return None

class JsonEncoder(object):
    def __init__(self) -> None:
        return

    def encode(self, project: Project, output_file: BufferedWriter) -> None:
        return