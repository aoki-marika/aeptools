from io import BufferedReader, BufferedWriter
from enum import Enum
from typing import Union
from .aep import Project, Texture, Composition, BlendMode, Layer, TextureLayer, CompositionLayer, ColourLayer

ENDIANNESS = 'little'

class Architecture(Enum):
    X86 = 'x86'
    X64 = 'x64'

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

    def read_f32(self) -> int:
        return float.from_bytes(self.file.read(0x4), ENDIANNESS)

    def read_pointer(self) -> int:
        return {
            Architecture.X86: self.read_u32,
            Architecture.X64: self.read_u64,
        }[self.architecture]()

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
        # counts are always the same size as pointers
        return self.read_pointer()

class AssetType(Enum):
    # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#type

    TEXTURE = 0x0
    COMPOSITION = 0x1

class LayerType(Enum):
    # https://github.com/aoki-marika/aeptools/wiki/Format-(x86-and-x64)#contents-type

    COMPOSITION = 0x4
    COLOUR = 0x6
    TEXTURE = 0x7

class BinaryDecoder(object):
    def __init__(self, architecture: Architecture) -> None:
        self.architecture = architecture

    def decode(self, input_file: BufferedReader) -> Project:
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
            assert(size == 20)
        elif self.architecture == Architecture.X64:
            name = reader.read_string()
            size = reader.read_u16()
            type = AssetType(reader.read_u16())
            width = reader.read_u16()
            height = reader.read_u16()
            layers_pointer = reader.read_pointer()
            num_layers = reader.read_count()
            assert(size == 32)

        if type == AssetType.TEXTURE:
            assert(num_layers == 0)
            assert(layers_pointer == 0x0)
            asset = Texture(name, width, height)
        elif type == AssetType.COMPOSITION:
            assert(layers_pointer != 0x0)

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
        type = LayerType((type_blend_mode >> 4) & 0xf)
        blend_mode = BlendMode(type_blend_mode & 0xf)

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

        if self.architecture == Architecture.X86:
            assert(size == 56)
        elif self.architecture == Architecture.X64:
            assert(size == 112)

        if type == LayerType.COMPOSITION:
            return CompositionLayer(name, blend_mode)
        elif type == LayerType.COLOUR:
            return ColourLayer(name, blend_mode)
        elif type == LayerType.TEXTURE:
            return TextureLayer(name, blend_mode)

        # ensure the cursor is reset for array reading
        reader.seek(pointer + size)

class BinaryEncoder(object):
    def __init__(self, architecture: Architecture) -> None:
        self.architecture = architecture

    def encode(self, project: Project, output_file: BufferedWriter) -> None:
        return