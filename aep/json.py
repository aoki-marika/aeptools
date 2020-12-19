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
        with input_path.open('r') as input_file:
            input = json.load(input_file)

            textures = self._decode_textures(input['textures'])
            compositions = self._decode_compositions(input['compositions'])

            return Project(textures, compositions)

    def _decode_textures(self, input: Dict[str, Any]) -> Sequence[Texture]:
        textures = []
        for name in input.keys():
            width = int(input[name]['width'])
            height = int(input[name]['height'])

            self._assert_u16(width, f'texture \'{name}\' width')
            self._assert_u16(height, f'texture \'{name}\' height')

            textures.append(Texture(name, width, height))

        return textures

    def _decode_compositions(self, input: Dict[str, Any]) -> Sequence[Composition]:
        compositions = []
        for name in input.keys():
            width = int(input[name]['width'])
            height = int(input[name]['height'])

            self._assert_u16(width, f'composition \'{name}\' width')
            self._assert_u16(height, f'composition \'{name}\' height')

            layers = []
            for layer in input[name]['layers']:
                layers.append(self._decode_layer(layer))

            compositions.append(Composition(name, width, height, layers))

        return compositions

    def _decode_layer(self, input: Dict[str, Any]) -> Layer:
        name = input['name']
        type = LAYER_TYPES[input['type']]
        blend_mode = BLEND_MODES[input['blend_mode']]
        timeline_start = int(input['timeline_start']) if input['timeline_start'] != None else None
        timeline_unknown1 = int(input['timeline_unknown1']) if input['timeline_unknown1'] != None else None
        timeline_duration = int(input['timeline_duration']) if input['timeline_duration'] != None else None
        timeline_unknown2 = int(input['timeline_unknown2']) if input['timeline_unknown2'] != None else None

        self._assert_u16(timeline_start, f'layer \'{name}\' timeline_start')
        self._assert_u16(timeline_unknown1, f'layer \'{name}\' timeline_unknown1')
        self._assert_u16(timeline_duration, f'layer \'{name}\' timeline_duration')
        self._assert_u32(timeline_unknown2, f'layer \'{name}\' timeline_unknown2')

        return Layer(
            name,
            type,
            blend_mode,
            timeline_start,
            timeline_unknown1,
            timeline_duration,
            timeline_unknown2,
            self._decode_keyframes(input.get('position_keyframes'), self._decode_position_keyframe),
            self._decode_keyframes(input.get('anchor_point_keyframes'), self._decode_anchor_point_keyframe),
            self._decode_keyframes(input.get('colour_keyframes'), self._decode_colour_keyframe),
            self._decode_keyframes(input.get('scale_keyframes'), self._decode_scale_keyframe),
            self._decode_keyframes(input.get('alpha_keyframes'), self._decode_alpha_keyframe),
            self._decode_keyframes(input.get('rotation_x_keyframes'), self._decode_rotation_keyframe),
            self._decode_keyframes(input.get('rotation_y_keyframes'), self._decode_rotation_keyframe),
            self._decode_keyframes(input.get('rotation_z_keyframes'), self._decode_rotation_keyframe),
            self._decode_keyframes(input.get('size_keyframes'), self._decode_size_keyframe),
            self._decode_keyframes(input.get('markers'), self._decode_marker_keyframe)
        )

    def _decode_keyframes(self, input: Optional[Sequence[Dict[str, Any]]], decode_keyframe: Callable[[int, Dict[str, Any]], Keyframe]) -> Optional[Sequence[Keyframe]]:
        if input == None:
            return None

        keyframes = []
        for keyframe in input:
            frame = int(keyframe['frame'])

            self._assert_u16(frame, 'keyframe frame')

            keyframes.append(decode_keyframe(frame, keyframe))

        # empty keyframes should still be treated as null
        if not keyframes:
            return None

        return keyframes

    def _decode_position_keyframe(self, frame: int, input: Dict[str, Any]) -> PositionKeyframe:
        x = float(input['x'])
        y = float(input['y'])
        z = float(input['z'])

        return PositionKeyframe(frame, x, y, z)

    def _decode_anchor_point_keyframe(self, frame: int, input: Dict[str, Any]) -> AnchorPointKeyframe:
        x = float(input['x'])
        y = float(input['y'])
        z = float(input['z'])

        return AnchorPointKeyframe(frame, x, y, z)

    def _decode_colour_keyframe(self, frame: int, input: Dict[str, Any]) -> ColourKeyframe:
        input = input['rgba']
        if not input.startswith('#'):
            raise ValueError(f'invalid rgba colour ({hex})')

        hex = input[1:]
        if len(hex) != 8:
            raise ValueError(f'invalid rgba colour ({hex})')

        rgba = int.from_bytes(bytes.fromhex(hex), 'big')
        r = (rgba >> 24) & 0xff
        g = (rgba >> 16) & 0xff
        b = (rgba >> 8) & 0xff
        a = rgba & 0xff

        return ColourKeyframe(frame, r, g, b, a)

    def _decode_scale_keyframe(self, frame: int, input: Dict[str, Any]) -> ScaleKeyframe:
        x = float(input['x'])
        y = float(input['y'])

        return ScaleKeyframe(frame, x, y)

    def _decode_alpha_keyframe(self, frame: int, input: Dict[str, Any]) -> AlphaKeyframe:
        value = float(input['value'])

        return AlphaKeyframe(frame, value)

    def _decode_rotation_keyframe(self, frame: int, input: Dict[str, Any]) -> RotationKeyframe:
        degrees = float(input['degrees'])

        return RotationKeyframe(frame, degrees)

    def _decode_size_keyframe(self, frame: int, input: Dict[str, Any]) -> SizeKeyframe:
        width = int(input['width'])
        height = int(input['height'])

        self._assert_u16(width, 'size keyframe width')
        self._assert_u16(height, 'size keyframe height')

        return SizeKeyframe(frame, width, height)

    def _decode_marker_keyframe(self, frame: int, input: Dict[str, Any]) -> Marker:
        unknown = int(input['unknown'])
        name = input['name']

        self._assert_u32(unknown, 'marker unknown')

        return Marker(frame, unknown, name)

    def _assert_un(self, value: Optional[int], name: str, num_bits: int) -> None:
        if value == None:
            return

        if value < 0 or value >= (2**num_bits):
            raise ValueError(f'{name} ({value}) is outside of bounds (0 to {(2**num_bits) - 1})')

    def _assert_u16(self, value: Optional[int], name: str) -> None:
        self._assert_un(value, name, 16)

    def _assert_u32(self, value: Optional[int], name: str) -> None:
        self._assert_un(value, name, 32)

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
        output = {
            'name': layer.name,
            'type': next(iter([k for k, v in iter(LAYER_TYPES.items()) if v == layer.type])),
            'blend_mode': next(iter([k for k, v in iter(BLEND_MODES.items()) if v == layer.blend_mode])),
            'timeline_start': layer.timeline_start,
            'timeline_unknown1': layer.timeline_unknown1,
            'timeline_duration': layer.timeline_duration,
            'timeline_unknown2': layer.timeline_unknown2,
        }

        if layer.position_keyframes != None:
            output['position_keyframes'] = self._encode_keyframes(layer.position_keyframes, self._encode_position_keyframe),

        if layer.anchor_point_keyframes != None:
            output['anchor_point_keyframes'] = self._encode_keyframes(layer.anchor_point_keyframes, self._encode_anchor_point_keyframe),

        if layer.colour_keyframes != None:
            output['colour_keyframes'] = self._encode_keyframes(layer.colour_keyframes, self._encode_colour_keyframe),

        if layer.scale_keyframes != None:
            output['scale_keyframes'] = self._encode_keyframes(layer.scale_keyframes, self._encode_scale_keyframe),

        if layer.alpha_keyframes != None:
            output['alpha_keyframes'] = self._encode_keyframes(layer.alpha_keyframes, self._encode_alpha_keyframe),

        if layer.rotation_x_keyframes != None:
            output['rotation_x_keyframes'] = self._encode_keyframes(layer.rotation_x_keyframes, self._encode_rotation_keyframe),

        if layer.rotation_y_keyframes != None:
            output['rotation_y_keyframes'] = self._encode_keyframes(layer.rotation_y_keyframes, self._encode_rotation_keyframe),

        if layer.rotation_z_keyframes != None:
            output['rotation_z_keyframes'] = self._encode_keyframes(layer.rotation_z_keyframes, self._encode_rotation_keyframe),

        if layer.size_keyframes != None:
            output['size_keyframes'] = self._encode_keyframes(layer.size_keyframes, self._encode_size_keyframe),

        if layer.markers != None:
            output['markers'] = self._encode_keyframes(layer.markers, self._encode_marker_keyframe),

        return output

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