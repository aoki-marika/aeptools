from io import BufferedReader, BufferedWriter
from enum import Enum
from .aep import Project

class Architecture(Enum):
    X86 = 'x86'
    X64 = 'x64'

class BinaryReader(object):
    def __init__(self, architecture: Architecture) -> None:
        return

class BinaryDecoder(object):
    def __init__(self, architecture: Architecture) -> None:
        self.reader = BinaryReader(architecture)

    def decode(self, input_file: BufferedReader) -> Project:
        return None

class BinaryEncoder(object):
    def __init__(self, architecture: Architecture) -> None:
        self.reader = BinaryReader(architecture)

    def encode(self, project: Project, output_file: BufferedWriter) -> None:
        return