import argparse
from enum import Enum
from pathlib import Path
from aep import Architecture, BinaryDecoder, JsonDecoder, BinaryEncoder, JsonEncoder

class Format(Enum):
    X86 = 'x86'
    X64 = 'x64'
    JSON = 'json'

    def __str__(self):
        return self.value

DECODERS = {
    Format.X86: BinaryDecoder(Architecture.X86),
    Format.X64: BinaryDecoder(Architecture.X64),
    Format.JSON: JsonDecoder(),
}

ENCODERS = {
    Format.X86: BinaryEncoder(Architecture.X86),
    Format.X64: BinaryEncoder(Architecture.X64),
    Format.JSON: JsonEncoder(),
}

def main() -> None:
    parser = argparse.ArgumentParser(description='Convert between binary and human-readable JSON AEP files.')

    input_group = parser.add_argument_group('input')
    input_group.add_argument('--input', dest='input_path', help='input file', type=Path, required=True)
    input_group.add_argument('--input-format', dest='input_format', help='input file format', type=Format, choices=list(Format), required=True)

    input_group = parser.add_argument_group('output')
    input_group.add_argument('--output', dest='output_path', help='output file', type=Path, required=True)
    input_group.add_argument('--output-format', dest='output_format', help='output file format', type=Format, choices=list(Format), required=True)

    args = parser.parse_args()

    print(f'{args.input_path} ({args.input_format})', '->', f'{args.output_path} ({args.output_format})')
    project = DECODERS[args.input_format].decode(args.input_path)
    ENCODERS[args.output_format].encode(project, args.output_path)

if __name__ == '__main__':
    main()