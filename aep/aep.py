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
                if layer.type == LayerType.TEXTURE:
                    if not any(t.name == layer.asset_name for t in self.textures):
                        raise ValueError(f'layer \'{layer.name}\' references unknown texture ({layer.asset_name})')
                elif layer.type == LayerType.COMPOSITION:
                    if not any(c.name == layer.asset_name for c in self.compositions):
                        raise ValueError(f'layer \'{layer.name}\' references unknown composition ({layer.asset_name})')

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

class LayerType(Enum):
    COMPOSITION = 0
    COLOUR = 1
    TEXTURE = 2

class BlendMode(Enum):
    NORMAL = 0
    ADDITIVE = 1
    UNKNOWN = 2

class PositionKeyframe:
    pass

class AnchorPointKeyframe:
    pass

class ColourKeyframe:
    pass

class ScaleKeyframe:
    pass

class AlphaKeyframe:
    pass

class RotationKeyframe:
    pass

class SizeKeyframe:
    pass

class Marker:
    pass

class Layer(object):
    def __init__(
        self,
        name: str,
        type: LayerType,
        blend_mode: BlendMode,
        timeline_start: Optional[int],
        timeline_unknown1: Optional[int],
        timeline_duration: Optional[int],
        timeline_unknown2: Optional[int],
        position_keyframes: Optional[Sequence[PositionKeyframe]],
        anchor_point_keyframes: Optional[Sequence[AnchorPointKeyframe]],
        colour_keyframes: Optional[Sequence[ColourKeyframe]],
        scale_keyframes: Optional[Sequence[ScaleKeyframe]],
        alpha_keyframes: Optional[Sequence[AlphaKeyframe]],
        rotation_x_keyframes: Optional[Sequence[RotationKeyframe]],
        rotation_y_keyframes: Optional[Sequence[RotationKeyframe]],
        rotation_z_keyframes: Optional[Sequence[RotationKeyframe]],
        size_keyframes: Optional[Sequence[SizeKeyframe]],
        markers: Optional[Sequence[Marker]],
    ) -> None:
        self.name = name
        self.type = type
        self.blend_mode = blend_mode
        self.timeline_start = timeline_start
        self.timeline_unknown1 = timeline_unknown1
        self.timeline_duration = timeline_duration
        self.timeline_unknown2 = timeline_unknown2
        self.position_keyframes = position_keyframes
        self.anchor_point_keyframes = anchor_point_keyframes
        self.colour_keyframes = colour_keyframes
        self.scale_keyframes = scale_keyframes
        self.alpha_keyframes = alpha_keyframes
        self.rotation_x_keyframes = rotation_x_keyframes
        self.rotation_y_keyframes = rotation_y_keyframes
        self.rotation_z_keyframes = rotation_z_keyframes
        self.size_keyframes = size_keyframes
        self.markers = markers

    @property
    def asset_name(self):
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#layer

        if '-' in self.name:
            return self.name.split('-')[1]
        else:
            return self.name

class Keyframe(object):
    def __init__(self, frame: int) -> None:
        self.frame = frame

class PositionKeyframe(Keyframe):
    def __init__(self, frame: int, x: float, y: float, z: float):
        super().__init__(frame)
        self.x = x
        self.y = y
        self.z = z

class AnchorPointKeyframe(Keyframe):
    def __init__(self, frame: int, x: float, y: float, z: float):
        super().__init__(frame)
        self.x = x
        self.y = y
        self.z = z

class ColourKeyframe(Keyframe):
    def __init__(self, frame: int, r: int, g: int, b: int, a: int):
        super().__init__(frame)
        self.r = r
        self.g = g
        self.b = b
        self.a = a

class ScaleKeyframe(Keyframe):
    def __init__(self, frame: int, x: float, y: float):
        super().__init__(frame)
        self.x = x
        self.y = y

class AlphaKeyframe(Keyframe):
    def __init__(self, frame: int, value: float):
        super().__init__(frame)
        self.value = value

class RotationKeyframe(Keyframe):
    def __init__(self, frame: int, degrees: float):
        super().__init__(frame)
        self.degrees = degrees

class SizeKeyframe(Keyframe):
    def __init__(self, frame: int, width: int, height: int):
        super().__init__(frame)
        self.width = width
        self.height = height

class Marker(Keyframe):
    def __init__(self, frame: int, unknown: int, name: str):
        super().__init__(frame)
        self.unknown = unknown
        self.name = name