from enum import Enum
from typing import Optional, Sequence

class Texture:
    pass

class Composition:
    pass

class Project(object):
    def __init__(self, textures: Sequence[Texture], compositions: Sequence[Composition]) -> None:
        self.textures = textures
        self.compositions = compositions

        # ensure there are no invalid asset references
        for composition in compositions:
            for layer in composition.layers:
                if isinstance(layer, TextureLayer):
                    assert(any(t.name == layer.asset_name for t in self.textures))
                elif isinstance(layer, CompositionLayer):
                    assert(any(c.name == layer.asset_name for c in self.compositions))

class Texture(object):
    def __init__(self, name: str, width: int, height: int) -> None:
        self.name = name
        self.width = width
        self.height = height

class Layer:
    pass

class Composition(object):
    def __init__(self, name: str, width: int, height: int, layers: Sequence[Layer]) -> None:
        self.name = name
        self.width = width
        self.height = height
        self.layers = layers

class BlendMode(Enum):
    # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#blend-mode

    NORMAL = 0x2
    ADDITIVE = 0x4
    UNKNOWN = 0x5

class Layer(object):
    def __init__(self, name: str, blend_mode: BlendMode) -> None:
        self.name = name
        self.blend_mode = blend_mode

    @property
    def asset_name(self):
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#layer

        if '-' in self.name:
            return self.name.split('-')[1]
        else:
            return self.name

class TextureLayer(Layer):
    pass

class CompositionLayer(Layer):
    pass

class ColourLayer(Layer):
    pass