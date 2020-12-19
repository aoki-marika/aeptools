# aeptools

Tools for working with KONAMI's proprietary AEP file format.

See the [Wiki](https://github.com/aoki-marika/aep/wiki) for documentation on the format.

# Tools

## aepconvert.py

Allows converting between x86/x64 and JSON AEP files for inspection and modification.

```
usage: aepconvert.py [-h] --input INPUT_PATH --input-format {x86,x64,json}
                     --output OUTPUT_PATH --output-format {x86,x64,json}

Convert between binary and human-readable JSON AEP files.

optional arguments:
  -h, --help            show this help message and exit

input:
  --input INPUT_PATH    input file
  --input-format {x86,x64,json}
                        input file format

output:
  --output OUTPUT_PATH  output file
  --output-format {x86,x64,json}
                        output file format

```

Generally, for modding, the workflow would look like this:

* Convert to JSON:
```
aepconvert.py --input aep_x64/target.bin --input-format x64 --output target.json --output-format json
```
* Make modifications.
* Convert back to x86 and x64:
```
aepconvert.py --input target.json --input-format json --output aep/target.bin --output-format x86
aepconvert.py --input target.json --input-format json --output aep_x64/target.bin --output-format x64
```
* Launch the program to view changes.