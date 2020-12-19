import struct
from io import BufferedReader, BufferedWriter, BytesIO
from enum import Enum
from typing import Optional, Union, Callable, Sequence, Dict
from pathlib import Path
from .aep import Project, Texture, Composition, Layer, LayerType, BlendMode, Keyframe, PositionKeyframe, AnchorPointKeyframe, ColourKeyframe, ScaleKeyframe, AlphaKeyframe, RotationKeyframe, SizeKeyframe, Marker

ENDIANNESS = 'little'

LAYER_TYPES = {
    0x4: LayerType.COMPOSITION,
    0x6: LayerType.COLOUR,
    0x7: LayerType.TEXTURE,
}

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

ASSET_TERMINATOR_SIZE = {
    Architecture.X86: 16,
    Architecture.X64: 16,
}

LAYERS_SECTION_POINTER_SIZE = {
    Architecture.X86: 16,
    Architecture.X64: 16,
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

    def read_u8(self) -> int:
        return int.from_bytes(self.file.read(0x1), ENDIANNESS)

    def read_u16(self) -> int:
        return int.from_bytes(self.file.read(0x2), ENDIANNESS)

    def read_u32(self) -> int:
        return int.from_bytes(self.file.read(0x4), ENDIANNESS)

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
    TEXTURE = 0x0
    COMPOSITION = 0x1

class BinaryDecoder(object):
    def __init__(self, architecture: Architecture) -> None:
        self.architecture = architecture

    def decode(self, input_path: Path) -> Project:
        with input_path.open('rb') as input_file:
            reader = BinaryReader(input_file, self.architecture)

            assets = []
            while reader.peek(ASSET_TERMINATOR_SIZE[self.architecture]) != (b'\0' * ASSET_TERMINATOR_SIZE[self.architecture]):
                assets.append(self._decode_asset(reader))

            textures = [a for a in assets if isinstance(a, Texture)]
            compositions = [a for a in assets if isinstance(a, Composition)]
            return Project(textures, compositions)

    def _decode_asset(self, reader: BinaryReader) -> Union[Texture, Composition]:
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
        if size != POSITION_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'position keyframe not {POSITION_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        x = reader.read_f32()
        y = reader.read_f32()
        z = reader.read_f32()
        return PositionKeyframe(frame, x, y, z)

    def _decode_anchor_point_keyframe(self, size: int, frame: int, reader: BinaryReader) -> AnchorPointKeyframe:
        if size != ANCHOR_POINT_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'anchor point keyframe not {ANCHOR_POINT_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        # re-normalize from 0-100 to 0-1, for consistency
        x = reader.read_f32() / 100
        y = reader.read_f32() / 100
        z = reader.read_f32() / 100

        return AnchorPointKeyframe(frame, x, y, z)

    def _decode_colour_keyframe(self, size: int, frame: int, reader: BinaryReader) -> ColourKeyframe:
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
        if size != SCALE_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'scale keyframe not {SCALE_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        # re-normalize from 0-100 to 0-1, for consistency
        x = reader.read_f32() / 100
        y = reader.read_f32() / 100

        return ScaleKeyframe(frame, x, y)

    def _decode_alpha_keyframe(self, size: int, frame: int, reader: BinaryReader) -> AlphaKeyframe:
        if size != ALPHA_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'alpha keyframe not {ALPHA_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        # re-normalize from 0-100 to 0-1, for consistency
        value = reader.read_f32() / 100

        return AlphaKeyframe(frame, value)

    def _decode_rotation_keyframe(self, size: int, frame: int, reader: BinaryReader) -> RotationKeyframe:
        if size != ROTATION_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'rotation keyframe not {ROTATION_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        degrees = reader.read_f32()
        return RotationKeyframe(frame, degrees)

    def _decode_size_keyframe(self, size: int, frame: int, reader: BinaryReader) -> SizeKeyframe:
        if size != SIZE_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'size keyframe not {SIZE_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        width = reader.read_u16()
        height = reader.read_u16()
        return SizeKeyframe(frame, width, height)

    def _decode_marker_keyframe(self, size: int, frame: int, reader: BinaryReader) -> Marker:
        if size != MARKER_KEYFRAME_SIZE[self.architecture]:
            raise ValueError(f'marker keyframe not {size != MARKER_KEYFRAME_SIZE[self.architecture]} bytes ({size})')

        unknown = reader.read_u32()
        name = reader.read_string()
        return Marker(frame, unknown, name)

class BinaryWriter(object):
    def __init__(self, architecture: Architecture) -> None:
        self.buffer = BytesIO()
        self.architecture = architecture

    def tell(self) -> int:
        return self.buffer.tell()

    def write_u8(self, value: int) -> None:
        self.buffer.write(value.to_bytes(0x1, ENDIANNESS))

    def write_u16(self, value: int) -> None:
        self.buffer.write(value.to_bytes(0x2, ENDIANNESS))

    def write_u32(self, value: int) -> None:
        self.buffer.write(value.to_bytes(0x4, ENDIANNESS))

    def write_f32(self, value: int) -> None:
        self.buffer.write(struct.pack('<f', value))

    def write_pointer(self, value: int) -> None:
        self.buffer.write(value.to_bytes(POINTER_SIZE[self.architecture], ENDIANNESS))

    def write_count(self, value: int) -> None:
        self.buffer.write(value.to_bytes(COUNT_SIZE[self.architecture], ENDIANNESS))

    def write_terminator(self, size: int) -> None:
        self.buffer.write(b'\0' * size)

    def write_to_file(self, file: BufferedWriter) -> None:
        file.write(self.buffer.getvalue())

class BinaryStringWriter(BinaryWriter):
    def __init__(self, architecture: Architecture):
        super().__init__(architecture)
        self.pointers = {}

    def write_string(self, value: str) -> int:
        # reuse strings so they arent duplicated
        # in larger files this is very useful for reducing size
        if value not in self.pointers:
            self.pointers[value] = self.tell()
            self.buffer.write(value.encode('ascii'))
            self.write_terminator(1)

        return self.pointers[value]

class SectionPointers(object):
    def __init__(self, assets_size: int, layers_size: int, keyframes_size: int, strings_size: int):
        self.assets_size = assets_size
        self.layers_size = layers_size
        self.keyframes_size = keyframes_size
        self.strings_size = strings_size

        self.assets = 0x0
        self.layers = self.assets + assets_size
        self.keyframes = self.layers + layers_size
        self.strings = self.keyframes + keyframes_size

class BinaryEncoder(object):
    def __init__(self, architecture: Architecture) -> None:
        self.architecture = architecture

    def encode(self, project: Project, output_path: Path) -> None:
        with output_path.open('wb+') as output_file:
            # separate each section into a different writer so pointers are easier to work with
            # note that the order and sectioning is important to keep intact,
            # as libaep expects a very specific layout for its files
            section_pointers = self._get_section_pointers(project)
            assets_writer = BinaryWriter(self.architecture)
            layers_writer = BinaryWriter(self.architecture)
            keyframes_writer = BinaryWriter(self.architecture)
            strings_writer = BinaryStringWriter(self.architecture)

            for texture in project.textures:
                self._encode_texture(texture, section_pointers, assets_writer, strings_writer)

            for composition in project.compositions:
                self._encode_composition(composition, section_pointers, assets_writer, layers_writer, keyframes_writer, strings_writer)

            assets_writer.write_terminator(ASSET_TERMINATOR_SIZE[self.architecture])
            assets_writer.write_pointer(section_pointers.layers)
            assets_writer.write_terminator(LAYERS_SECTION_POINTER_SIZE[self.architecture] - POINTER_SIZE[self.architecture])

            # ensure the pre-calculated section sizes match up with the written sizes, for quick error checking
            if assets_writer.tell() != section_pointers.assets_size:
                raise ValueError(f'expected to write {section_pointers.assets_size} assets section bytes, but wrote {assets_writer.tell()}')

            if layers_writer.tell() != section_pointers.layers_size:
                raise ValueError(f'expected to write {section_pointers.layers_size} layers section bytes, but wrote {layers_writer.tell()}')

            if keyframes_writer.tell() != section_pointers.keyframes_size:
                raise ValueError(f'expected to write {section_pointers.keyframes_size} keyframes section bytes, but wrote {keyframes_writer.tell()}')

            if strings_writer.tell() != section_pointers.strings_size:
                raise ValueError(f'expected to write {section_pointers.strings_size} strings section bytes, but wrote {strings_writer.tell()}')

            assets_writer.write_to_file(output_file)
            layers_writer.write_to_file(output_file)
            keyframes_writer.write_to_file(output_file)
            strings_writer.write_to_file(output_file)

    def _get_section_pointers(self, project: Project) -> SectionPointers:
        assets_size = 0
        layers_size = 0
        keyframes_size = 0
        strings_size = 0

        existing_strings = []

        for texture in project.textures:
            assets_size += ASSET_SIZE[self.architecture]

            if texture.name not in existing_strings:
                strings_size += self._get_string_encoded_size(texture.name)
                existing_strings.append(texture.name)

        for composition in project.compositions:
            assets_size += ASSET_SIZE[self.architecture]

            if composition.name not in existing_strings:
                strings_size += self._get_string_encoded_size(composition.name)
                existing_strings.append(composition.name)

            for layer in composition.layers:
                layers_size += LAYER_SIZE[self.architecture]

                if layer.name not in existing_strings:
                    strings_size += self._get_string_encoded_size(layer.name)
                    existing_strings.append(layer.name)

                if layer.has_timeline:
                    keyframes_size += LAYER_TIMELINE_SIZE[self.architecture]

                # +1 for each keyframe count for the terminator

                if layer.position_keyframes != None:
                    keyframes_size += POSITION_KEYFRAME_SIZE[self.architecture] * (len(layer.position_keyframes) + 1)

                if layer.anchor_point_keyframes != None:
                    keyframes_size += ANCHOR_POINT_KEYFRAME_SIZE[self.architecture] * (len(layer.anchor_point_keyframes) + 1)

                if layer.colour_keyframes != None:
                    keyframes_size += COLOUR_KEYFRAME_SIZE[self.architecture] * (len(layer.colour_keyframes) + 1)

                if layer.scale_keyframes != None:
                    keyframes_size += SCALE_KEYFRAME_SIZE[self.architecture] * (len(layer.scale_keyframes) + 1)

                if layer.alpha_keyframes != None:
                    keyframes_size += ALPHA_KEYFRAME_SIZE[self.architecture] * (len(layer.alpha_keyframes) + 1)

                if layer.rotation_x_keyframes != None:
                    keyframes_size += ROTATION_KEYFRAME_SIZE[self.architecture] * (len(layer.rotation_x_keyframes) + 1)

                if layer.rotation_y_keyframes != None:
                    keyframes_size += ROTATION_KEYFRAME_SIZE[self.architecture] * (len(layer.rotation_y_keyframes) + 1)

                if layer.rotation_z_keyframes != None:
                    keyframes_size += ROTATION_KEYFRAME_SIZE[self.architecture] * (len(layer.rotation_z_keyframes) + 1)

                if layer.size_keyframes != None:
                    keyframes_size += SIZE_KEYFRAME_SIZE[self.architecture] * (len(layer.size_keyframes) + 1)

                if layer.markers != None:
                    keyframes_size += MARKER_KEYFRAME_SIZE[self.architecture] * (len(layer.markers) + 1)
                    for keyframe in layer.markers:
                        if keyframe.name not in existing_strings:
                            strings_size += self._get_string_encoded_size(keyframe.name)
                            existing_strings.append(keyframe.name)

        assets_size += ASSET_TERMINATOR_SIZE[self.architecture]
        assets_size += LAYERS_SECTION_POINTER_SIZE[self.architecture]
        return SectionPointers(assets_size, layers_size, keyframes_size, strings_size)

    def _get_string_encoded_size(self, string: str) -> int:
        # characters + null terminator
        return len(string.encode('ascii')) + 1

    def _encode_texture(self, texture: Texture, section_pointers: SectionPointers, assets_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        self._encode_asset(
            texture.name,
            AssetType.TEXTURE,
            texture.width,
            texture.height,
            0,
            0x0,
            section_pointers,
            assets_writer,
            strings_writer
        )

    def _encode_composition(self, composition: Composition, section_pointers: SectionPointers, assets_writer: BinaryWriter, layers_writer: BinaryWriter, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        layers_pointer = section_pointers.layers + layers_writer.tell()
        self._encode_asset(
            composition.name,
            AssetType.COMPOSITION,
            composition.width,
            composition.height,
            len(composition.layers),
            layers_pointer,
            section_pointers,
            assets_writer,
            strings_writer
        )

        for layer in composition.layers:
            self._encode_layer(layer, section_pointers, layers_writer, keyframes_writer, strings_writer)

    def _encode_asset(self, name: str, type: AssetType, width: int, height: int, num_layers: int, layers_pointer: int, section_pointers: SectionPointers, assets_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        name_pointer = section_pointers.strings + strings_writer.write_string(name)

        if self.architecture == Architecture.X86:
            assets_writer.write_u16(ASSET_SIZE[self.architecture])
            assets_writer.write_u16(type.value)
            assets_writer.write_pointer(name_pointer)
            assets_writer.write_u16(width)
            assets_writer.write_u16(height)
            assets_writer.write_count(num_layers)
            assets_writer.write_pointer(layers_pointer)
        elif self.architecture == Architecture.X64:
            assets_writer.write_pointer(name_pointer)
            assets_writer.write_u16(ASSET_SIZE[self.architecture])
            assets_writer.write_u16(type.value)
            assets_writer.write_u16(width)
            assets_writer.write_u16(height)
            assets_writer.write_pointer(layers_pointer)
            assets_writer.write_count(num_layers)

    def _encode_layer(self, layer: Layer, section_pointers: SectionPointers, layers_writer: BinaryWriter, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        type = next(iter([k for k, v in iter(LAYER_TYPES.items()) if v == layer.type]))
        blend_mode = next(iter([k for k, v in iter(BLEND_MODES.items()) if v == layer.blend_mode]))

        layers_writer.write_u16(LAYER_SIZE[self.architecture])
        layers_writer.write_u8((type << 4) | blend_mode)
        layers_writer.write_u8(0x0)

        if self.architecture == Architecture.X64:
            layers_writer.write_u32(0x0)

        layers_writer.write_pointer(section_pointers.strings + strings_writer.write_string(layer.name))
        layers_writer.write_pointer(self._encode_timeline(layer, section_pointers, keyframes_writer))
        layers_writer.write_pointer(self._encode_keyframes(layer.position_keyframes, POSITION_KEYFRAME_SIZE, section_pointers, keyframes_writer, strings_writer, self._encode_position_keyframe))
        layers_writer.write_pointer(self._encode_keyframes(layer.anchor_point_keyframes, ANCHOR_POINT_KEYFRAME_SIZE, section_pointers, keyframes_writer, strings_writer, self._encode_anchor_point_keyframe))
        layers_writer.write_pointer(self._encode_keyframes(layer.colour_keyframes, COLOUR_KEYFRAME_SIZE, section_pointers, keyframes_writer, strings_writer, self._encode_colour_keyframe))
        layers_writer.write_pointer(self._encode_keyframes(layer.scale_keyframes, SCALE_KEYFRAME_SIZE, section_pointers, keyframes_writer, strings_writer, self._encode_scale_keyframe))
        layers_writer.write_pointer(self._encode_keyframes(layer.alpha_keyframes, ALPHA_KEYFRAME_SIZE, section_pointers, keyframes_writer, strings_writer, self._encode_alpha_keyframe))
        layers_writer.write_pointer(0x0)
        layers_writer.write_pointer(self._encode_keyframes(layer.rotation_x_keyframes, ROTATION_KEYFRAME_SIZE, section_pointers, keyframes_writer, strings_writer, self._encode_rotation_keyframe))
        layers_writer.write_pointer(self._encode_keyframes(layer.rotation_y_keyframes, ROTATION_KEYFRAME_SIZE, section_pointers, keyframes_writer, strings_writer, self._encode_rotation_keyframe))
        layers_writer.write_pointer(self._encode_keyframes(layer.rotation_z_keyframes, ROTATION_KEYFRAME_SIZE, section_pointers, keyframes_writer, strings_writer, self._encode_rotation_keyframe))
        layers_writer.write_pointer(self._encode_keyframes(layer.size_keyframes, SIZE_KEYFRAME_SIZE, section_pointers, keyframes_writer, strings_writer, self._encode_size_keyframe))
        layers_writer.write_pointer(self._encode_keyframes(layer.markers, MARKER_KEYFRAME_SIZE, section_pointers, keyframes_writer, strings_writer, self._encode_marker_keyframe))

    def _encode_timeline(self, layer: Layer, section_pointers: SectionPointers, keyframes_writer: BinaryWriter) -> int:
        if not layer.has_timeline:
            return 0x0

        pointer = section_pointers.keyframes + keyframes_writer.tell()

        keyframes_writer.write_u16(LAYER_TIMELINE_SIZE[self.architecture])
        keyframes_writer.write_u16(layer.timeline_start)
        keyframes_writer.write_u16(layer.timeline_unknown1)
        keyframes_writer.write_u16(layer.timeline_duration)
        keyframes_writer.write_u32(layer.timeline_unknown2)

        return pointer

    def _encode_keyframes(self, keyframes: Optional[Sequence[Keyframe]], size: Dict[Architecture, int], section_pointers: SectionPointers, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter, encode_keyframe: Callable[[Keyframe, SectionPointers, BinaryWriter, BinaryStringWriter], None]) -> int:
        if keyframes == None:
            return 0x0

        pointer = section_pointers.keyframes + keyframes_writer.tell()

        for keyframe in keyframes:
            keyframes_writer.write_u16(size[self.architecture])
            keyframes_writer.write_u16(keyframe.frame)
            encode_keyframe(keyframe, section_pointers, keyframes_writer, strings_writer)

        # write the terminator keyframe
        keyframes_writer.write_u16(size[self.architecture])
        keyframes_writer.write_u16(0xffff)
        keyframes_writer.write_terminator(size[self.architecture] - 0x4)

        return pointer

    def _encode_position_keyframe(self, keyframe: PositionKeyframe, section_pointers: SectionPointers, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        keyframes_writer.write_f32(keyframe.x)
        keyframes_writer.write_f32(keyframe.y)
        keyframes_writer.write_f32(keyframe.z)

    def _encode_anchor_point_keyframe(self, keyframe: AnchorPointKeyframe, section_pointers: SectionPointers, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        keyframes_writer.write_f32(keyframe.x * 100)
        keyframes_writer.write_f32(keyframe.y * 100)
        keyframes_writer.write_f32(keyframe.z * 100)

    def _encode_colour_keyframe(self, keyframe: ColourKeyframe, section_pointers: SectionPointers, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        keyframes_writer.write_u8(keyframe.r)
        keyframes_writer.write_u8(keyframe.g)
        keyframes_writer.write_u8(keyframe.b)
        keyframes_writer.write_u8(keyframe.a)

    def _encode_scale_keyframe(self, keyframe: ScaleKeyframe, section_pointers: SectionPointers, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        keyframes_writer.write_f32(keyframe.x * 100)
        keyframes_writer.write_f32(keyframe.y * 100)

    def _encode_alpha_keyframe(self, keyframe: AlphaKeyframe, section_pointers: SectionPointers, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        keyframes_writer.write_f32(keyframe.value * 100)

    def _encode_rotation_keyframe(self, keyframe: RotationKeyframe, section_pointers: SectionPointers, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        keyframes_writer.write_f32(keyframe.degrees)

    def _encode_size_keyframe(self, keyframe: SizeKeyframe, section_pointers: SectionPointers, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        keyframes_writer.write_u16(keyframe.width)
        keyframes_writer.write_u16(keyframe.height)

    def _encode_marker_keyframe(self, keyframe: Marker, section_pointers: SectionPointers, keyframes_writer: BinaryWriter, strings_writer: BinaryStringWriter) -> None:
        keyframes_writer.write_u32(keyframe.unknown)
        keyframes_writer.write_pointer(section_pointers.strings + strings_writer.write_string(keyframe.name))