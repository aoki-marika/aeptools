import struct
from io import BufferedReader, BufferedWriter
from enum import Enum
from typing import Optional, Union, Callable, Sequence
from pathlib import Path
from .aep import Project, Texture, Composition, Layer, LayerType, BlendMode, Keyframe, PositionKeyframe, AnchorPointKeyframe, ColourKeyframe, ScaleKeyframe, AlphaKeyframe, RotationKeyframe, SizeKeyframe, Marker

ENDIANNESS = 'little'

# https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#contents-type
LAYER_TYPES = {
    0x4: LayerType.COMPOSITION,
    0x6: LayerType.COLOUR,
    0x7: LayerType.TEXTURE,
}

# https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#blend-mode
BLEND_MODES = {
    0x2: BlendMode.NORMAL,
    0x4: BlendMode.ADDITIVE,
    0x5: BlendMode.UNKNOWN,
}

class Architecture(Enum):
    X86 = 'x86'
    X64 = 'x64'

POINTER_SIZE = {
    Architecture.X86: 0x4,
    Architecture.X64: 0x8,
}

COUNT_SIZE = {
    Architecture.X86: 0x4,
    Architecture.X64: 0x8,
}

ASSET_SIZE = {
    Architecture.X86: 20,
    Architecture.X64: 32,
}

LAYER_SIZE = {
    Architecture.X86: 56,
    Architecture.X64: 112,
}

LAYER_TIMELINE_SIZE = {
    Architecture.X86: 12,
    Architecture.X64: 12,
}

POSITION_KEYFRAME_SIZE = {
    Architecture.X86: 16,
    Architecture.X64: 16,
}

ANCHOR_POINT_KEYFRAME_SIZE = {
    Architecture.X86: 16,
    Architecture.X64: 16,
}

COLOUR_KEYFRAME_SIZE = {
    Architecture.X86: 8,
    Architecture.X64: 8,
}

SCALE_KEYFRAME_SIZE = {
    Architecture.X86: 12,
    Architecture.X64: 12,
}

ALPHA_KEYFRAME_SIZE = {
    Architecture.X86: 8,
    Architecture.X64: 8,
}

ROTATION_KEYFRAME_SIZE = {
    Architecture.X86: 8,
    Architecture.X64: 8,
}

SIZE_KEYFRAME_SIZE = {
    Architecture.X86: 8,
    Architecture.X64: 8,
}

MARKER_KEYFRAME_SIZE = {
    Architecture.X86: 12,
    Architecture.X64: 16,
}

class BinaryReader(object):
    def __init__(self, file: BufferedReader, architecture: Architecture) -> None:
        self.file = file
        self.architecture = architecture

    def seek(self, pointer: int) -> None:
        self.file.seek(pointer)

    def tell(self) -> int:
        return self.file.tell()

    def peek(self, num_bytes: int) -> bytes:
        return self.file.peek()[:num_bytes]

    # see https://github.com/aoki-marika/aeptools/wiki#data-types for data type information

    def read_u8(self) -> int:
        return int.from_bytes(self.file.read(0x1), ENDIANNESS)

    def read_u16(self) -> int:
        return int.from_bytes(self.file.read(0x2), ENDIANNESS)

    def read_u32(self) -> int:
        return int.from_bytes(self.file.read(0x4), ENDIANNESS)

    def read_u64(self) -> int:
        return int.from_bytes(self.file.read(0x8), ENDIANNESS)

    def read_f32(self) -> float:
        return struct.unpack('<f', self.file.read(0x4))[0]

    def read_pointer(self) -> int:
        return int.from_bytes(self.file.read(POINTER_SIZE[self.architecture]), ENDIANNESS)

    def read_string(self) -> str:
        pointer = self.read_pointer()
        return_cursor = self.tell()
        self.seek(pointer)

        result = ''
        while self.peek(1) != b'\0':
            result += chr(self.read_u8())

        self.seek(return_cursor)
        return result

    def read_count(self) -> int:
        return int.from_bytes(self.file.read(COUNT_SIZE[self.architecture]), ENDIANNESS)

class AssetType(Enum):
    # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#type

    TEXTURE = 0x0
    COMPOSITION = 0x1

class BinaryDecoder(object):
    def __init__(self, architecture: Architecture) -> None:
        self.architecture = architecture

    def decode(self, input_path: Path) -> Project:
        with input_path.open('rb') as input_file:
            reader = BinaryReader(input_file, self.architecture)

            # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#project

            assets = []
            while reader.peek(16) != (b'\0' * 16):
                assets.append(self._decode_asset(reader))

            textures = [a for a in assets if isinstance(a, Texture)]
            compositions = [a for a in assets if isinstance(a, Composition)]
            return Project(textures, compositions)

    def _decode_asset(self, reader: BinaryReader) -> Union[Texture, Composition]:
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#asset

        pointer = reader.tell()

        if self.architecture == Architecture.X86:
            size = reader.read_u16()
            type = AssetType(reader.read_u16())
            name = reader.read_string()
            width = reader.read_u16()
            height = reader.read_u16()
            num_layers = reader.read_count()
            layers_pointer = reader.read_pointer()
        elif self.architecture == Architecture.X64:
            name = reader.read_string()
            size = reader.read_u16()
            type = AssetType(reader.read_u16())
            width = reader.read_u16()
            height = reader.read_u16()
            layers_pointer = reader.read_pointer()
            num_layers = reader.read_count()

        if size != ASSET_SIZE[self.architecture]:
            raise ValueError(f'asset \'{name}\' not {ASSET_SIZE[self.architecture]} bytes ({size})')

        if type == AssetType.TEXTURE:
            if num_layers != 0 or layers_pointer != 0x0:
                raise ValueError(f'texture \'{name}\' has non-zero layers ({num_layers} at {hex(layers_pointer)})')

            asset = Texture(name, width, height)
        elif type == AssetType.COMPOSITION:
            if layers_pointer == 0x0:
                raise ValueError(f'composition \'{name}\' has null layers pointers ({num_layers} at {hex(layers_pointer)})')

            layers = []
            reader.seek(layers_pointer)
            for _ in range(0, num_layers):
                layers.append(self._decode_layer(reader))

            asset = Composition(name, width, height, layers)

        # ensure the cursor is reset for array reading
        reader.seek(pointer + size)
        return asset

    def _decode_layer(self, reader: BinaryReader) -> Layer:
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#layer

        pointer = reader.tell()

        size = reader.read_u16()
        type_blend_mode = reader.read_u8()
        type = LAYER_TYPES[(type_blend_mode >> 4) & 0xf]
        blend_mode = BLEND_MODES[type_blend_mode & 0xf]

        # padding
        assert(reader.read_u8() == 0x0)
        if self.architecture == Architecture.X64:
            assert(reader.read_u32() == 0x0)

        name = reader.read_string()
        timeline_pointer = reader.read_pointer()
        position_keyframes_pointer = reader.read_pointer()
        anchor_point_keyframes_pointer = reader.read_pointer()
        colour_keyframes_pointer = reader.read_pointer()
        scale_keyframes_pointer = reader.read_pointer()
        alpha_keyframes_pointer = reader.read_pointer()
        unknown_keyframes_pointer = reader.read_pointer()
        rotation_x_keyframes_pointer = reader.read_pointer()
        rotation_y_keyframes_pointer = reader.read_pointer()
        rotation_z_keyframes_pointer = reader.read_pointer()
        size_keyframes_pointer = reader.read_pointer()
        marker_keyframes_pointer = reader.read_pointer()

        if size != LAYER_SIZE[self.architecture]:
            raise ValueError(f'layer \'{name}\' not {LAYER_SIZE[self.architecture]} bytes ({size})')

        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#timeline
        if timeline_pointer != 0x0:
            reader.seek(timeline_pointer)
            timeline_size = reader.read_u16()
            timeline_start = reader.read_u16()
            timeline_unknown1 = reader.read_u16()
            timeline_duration = reader.read_u16()
            timeline_unknown2 = reader.read_u32()

            if timeline_size != LAYER_TIMELINE_SIZE[self.architecture]:
                raise ValueError(f'layer \'{name}\' timeline not {LAYER_TIMELINE_SIZE[self.architecture]} bytes ({timeline_size})')

            if timeline_unknown2 != 4096:
                raise ValueError(f'layer \'{name}\' unknown2 not 4096 ({timeline_unknown2})')
        else:
            timeline_start = None
            timeline_unknown1 = None
            timeline_duration = None
            timeline_unknown2 = None

        position_keyframes = self._decode_keyframes(reader, position_keyframes_pointer, self._decode_position_keyframe)
        anchor_point_keyframes = self._decode_keyframes(reader, anchor_point_keyframes_pointer, self._decode_anchor_point_keyframe)
        colour_keyframes = self._decode_keyframes(reader, colour_keyframes_pointer, self._decode_colour_keyframe)
        scale_keyframes = self._decode_keyframes(reader, scale_keyframes_pointer, self._decode_scale_keyframe)
        alpha_keyframes = self._decode_keyframes(reader, alpha_keyframes_pointer, self._decode_alpha_keyframe)

        # unused
        if unknown_keyframes_pointer != 0x0:
            raise ValueError(f'layer \'{name}\' has unknown keyframes at {hex(unknown_keyframes_pointer)}')

        rotation_x_keyframes = self._decode_keyframes(reader, rotation_x_keyframes_pointer, self._decode_rotation_keyframe)
        rotation_y_keyframes = self._decode_keyframes(reader, rotation_y_keyframes_pointer, self._decode_rotation_keyframe)
        rotation_z_keyframes = self._decode_keyframes(reader, rotation_z_keyframes_pointer, self._decode_rotation_keyframe)
        size_keyframes = self._decode_keyframes(reader, size_keyframes_pointer, self._decode_size_keyframe)
        markers = self._decode_keyframes(reader, marker_keyframes_pointer, self._decode_marker_keyframe)

        # ensure the cursor is reset for array reading
        reader.seek(pointer + size)
        return Layer(
            name,
            type,
            blend_mode,
            timeline_start,
            timeline_unknown1,
            timeline_duration,
            timeline_unknown2,
            position_keyframes,
            anchor_point_keyframes,
            colour_keyframes,
            scale_keyframes,
            alpha_keyframes,
            rotation_x_keyframes,
            rotation_y_keyframes,
            rotation_z_keyframes,
            size_keyframes,
            markers
        )

    def _decode_keyframes(self, reader: BinaryReader, pointer: int, decode_keyframe: Callable[[int, int, BinaryReader], Keyframe]) -> Optional[Sequence[Keyframe]]:
        if pointer == 0x0:
            return None

        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#keyframe

        keyframes = []
        reader.seek(pointer)
        while True:
            item_pointer = reader.tell()
            size = reader.read_u16()
            frame = reader.read_u16()
            if frame == 0xffff:
                break

            keyframes.append(decode_keyframe(size, frame, reader))

            # ensure the cursor is reset for array reading
            reader.seek(item_pointer + size)

        return keyframes

    def _decode_position_keyframe(self, size: int, frame: int, reader: BinaryReader) -> PositionKeyframe:
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#position

        if size != POSITION_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'position keyframe not {POSITION_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        x = reader.read_f32()
        y = reader.read_f32()
        z = reader.read_f32()
        return PositionKeyframe(frame, x, y, z)

    def _decode_anchor_point_keyframe(self, size: int, frame: int, reader: BinaryReader) -> AnchorPointKeyframe:
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#anchor-point

        if size != ANCHOR_POINT_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'anchor point keyframe not {ANCHOR_POINT_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        # re-normalize from 0-100 to 0-1, for consistency
        x = reader.read_f32() / 100
        y = reader.read_f32() / 100
        z = reader.read_f32() / 100

        return AnchorPointKeyframe(frame, x, y, z)

    def _decode_colour_keyframe(self, size: int, frame: int, reader: BinaryReader) -> ColourKeyframe:
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#colour

        # COLOUR_KEYFRAME_SIZE only accounts for rgba u8s, but decoding must also handle f32s
        if size != 8 and size != 20:
            raise ValueError(f'colour keyframe not 8 or 20 bytes ({size})')

        if size == 8:
            r = reader.read_u8()
            g = reader.read_u8()
            b = reader.read_u8()
            a = reader.read_u8()
        elif size == 20:
            # re-normalize from 0-1 (?) to 0-255, for consistency
            # TODO: ensure that this is actually rgba f32s from 0-1
            r = int(reader.read_f32() * 255)
            g = int(reader.read_f32() * 255)
            b = int(reader.read_f32() * 255)
            a = int(reader.read_f32() * 255)

        return ColourKeyframe(frame, r, g, b, a)

    def _decode_scale_keyframe(self, size: int, frame: int, reader: BinaryReader) -> ScaleKeyframe:
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#colour

        if size != SCALE_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'scale keyframe not {SCALE_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        # re-normalize from 0-100 to 0-1, for consistency
        x = reader.read_f32() / 100
        y = reader.read_f32() / 100

        return ScaleKeyframe(frame, x, y)

    def _decode_alpha_keyframe(self, size: int, frame: int, reader: BinaryReader) -> AlphaKeyframe:
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#alpha

        if size != ALPHA_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'alpha keyframe not {ALPHA_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        # re-normalize from 0-100 to 0-1, for consistency
        value = reader.read_f32() / 100

        return AlphaKeyframe(frame, value)

    def _decode_rotation_keyframe(self, size: int, frame: int, reader: BinaryReader) -> RotationKeyframe:
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#rotation

        if size != ROTATION_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'rotation keyframe not {ROTATION_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        degrees = reader.read_f32()
        return RotationKeyframe(frame, degrees)

    def _decode_size_keyframe(self, size: int, frame: int, reader: BinaryReader) -> SizeKeyframe:
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#size

        if size != SIZE_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'size keyframe not {SIZE_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        width = reader.read_u16()
        height = reader.read_u16()
        return SizeKeyframe(frame, width, height)

    def _decode_marker_keyframe(self, size: int, frame: int, reader: BinaryReader) -> Marker:
        # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#marker

        if size != MARKER_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'marker keyframe not {size != MARKER_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        unknown = reader.read_u32()
        name = reader.read_string()
        return Marker(frame, unknown, name)

class BinaryEncoder(object):
    def __init__(self, architecture: Architecture) -> None:
        self.architecture = architecture

    def encode(self, project: Project, output_path: Path) -> None:
        return