from typing import Sequence

class Texture:
    pass

class Composition:
    pass

class Project(object):
    def __init__(self, textures: Sequence[Texture], compositions: Sequence[Composition]) -> None:
        self.textures = textures
        self.compositions = compositions

class Texture(object):
    def __init__(self, name: str, width: int, height: int) -> None:
        self.name = name
        self.width = width
        self.height = height

class Composition(object):
    def __init__(self, name: str, width: int, height: int) -> None:
        self.name = name
        self.width = width
        self.height = height