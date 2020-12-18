import json
from io import BufferedReader, BufferedWriter
from typing import Optional, Dict, Sequence, Callable, Any
from pathlib import Path
from .aep import Project, Texture, Composition, Layer, LayerType, BlendMode, Keyframe, PositionKeyframe, AnchorPointKeyframe, ColourKeyframe, ScaleKeyframe, AlphaKeyframe, RotationKeyframe, SizeKeyframe, Marker

LAYER_TYPES = {
    'composition': LayerType.COMPOSITION,
    'colour': LayerType.COLOUR,
    'texture': LayerType.TEXTURE,
}

BLEND_MODES = {
    'normal': BlendMode.NORMAL,
    'additive': BlendMode.ADDITIVE,
    'unknown': BlendMode.UNKNOWN,
}

class JsonDecoder(object):
    def __init__(self) -> None:
        return

    def decode(self, input_path: Path) -> Project:
        return None

class JsonEncoder(object):
    def __init__(self) -> None:
        return

    def encode(self, project: Project, output_path: Path) -> None:
        with output_path.open('w+') as output_file:
            output = {
                'textures': {t.name: self._encode_texture(t) for t in project.textures},
                'compositions': {c.name: self._encode_composition(c) for c in project.compositions},
            }

            json.dump(output, output_file, indent=4)

    def _encode_texture(self, texture: Texture) -> Dict[str, Any]:
        return {
            'width': texture.width,
            'height': texture.height,
        }

    def _encode_composition(self, composition: Composition) -> Dict[str, Any]:
        return {
            'width': composition.width,
            'height': composition.height,
            'layers': [self._encode_layer(l) for l in composition.layers]
        }

    def _encode_layer(self, layer: Layer) -> Dict[str, Any]:
        return {
            'name': layer.name,
            'type': next(iter([k for k, v in iter(LAYER_TYPES.items()) if v == layer.type])),
            'blend_mode': next(iter([k for k, v in iter(BLEND_MODES.items()) if v == layer.blend_mode])),
            'timeline_start': layer.timeline_start,
            'timeline_unknown1': layer.timeline_unknown1,
            'timeline_duration': layer.timeline_duration,
            'timeline_unknown2': layer.timeline_unknown2,
            'position_keyframes': self._encode_keyframes(layer.position_keyframes, self._encode_position_keyframe),
            'anchor_point_keyframes': self._encode_keyframes(layer.anchor_point_keyframes, self._encode_anchor_point_keyframe),
            'colour_keyframes': self._encode_keyframes(layer.colour_keyframes, self._encode_colour_keyframe),
            'scale_keyframes': self._encode_keyframes(layer.scale_keyframes, self._encode_scale_keyframe),
            'alpha_keyframes': self._encode_keyframes(layer.alpha_keyframes, self._encode_alpha_keyframe),
            'rotation_x_keyframes': self._encode_keyframes(layer.rotation_x_keyframes, self._encode_rotation_keyframe),
            'rotation_y_keyframes': self._encode_keyframes(layer.rotation_y_keyframes, self._encode_rotation_keyframe),
            'rotation_z_keyframes': self._encode_keyframes(layer.rotation_z_keyframes, self._encode_rotation_keyframe),
            'size_keyframes': self._encode_keyframes(layer.size_keyframes, self._encode_size_keyframe),
            'markers': self._encode_keyframes(layer.markers, self._encode_marker_keyframe),
        }

    def _encode_keyframes(self, keyframes: Optional[Sequence[Keyframe]], encode_keyframe: Callable[[Keyframe], Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if keyframes == None:
            return None

        return [{ **{ 'frame': k.frame }, **encode_keyframe(k) } for k in keyframes]

    def _encode_position_keyframe(self, keyframe: PositionKeyframe) -> Dict[str, Any]:
        return {
            'x': keyframe.x,
            'y': keyframe.y,
            'z': keyframe.z,
        }

    def _encode_anchor_point_keyframe(self, keyframe: AnchorPointKeyframe) -> Dict[str, Any]:
        return {
            'x': keyframe.x,
            'y': keyframe.y,
            'z': keyframe.z,
        }

    def _encode_colour_keyframe(self, keyframe: ColourKeyframe) -> Dict[str, Any]:
        return {
            'rgba': "#{0:08x}".format((keyframe.r << 24) | (keyframe.g << 16) | (keyframe.b << 8) | (keyframe.a)),
        }

    def _encode_scale_keyframe(self, keyframe: ScaleKeyframe) -> Dict[str, Any]:
        return {
            'x': keyframe.x,
            'y': keyframe.y,
        }

    def _encode_alpha_keyframe(self, keyframe: AlphaKeyframe) -> Dict[str, Any]:
        return {
            'value': keyframe.value,
        }

    def _encode_rotation_keyframe(self, keyframe: RotationKeyframe) -> Dict[str, Any]:
        return {
            'rotation': keyframe.degrees,
        }

    def _encode_size_keyframe(self, keyframe: SizeKeyframe) -> Dict[str, Any]:
        return {
            'width': keyframe.width,
            'height': keyframe.height,
        }

    def _encode_marker_keyframe(self, keyframe: Marker) -> Dict[str, Any]:
        return {
            'unknown': keyframe.unknown,
            'name': keyframe.name,
        }