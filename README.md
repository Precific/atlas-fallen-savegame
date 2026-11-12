# Atlas Fallen savegame utility&stuff

# New GUI/Json Editor

Full .sav File loading Support including Json Editor GUI and Export Functionality Right from the Editor - no need for manual Export/Edit/Import no more !

Supports the release build of Atlas Fallen (2023-08-12). 

## Savegame extract/modify utility

The [savegame_body.py](savegame_body.py) script can unpack and repack the body portion of Atlas Fallen `.sav` files, either raw or as a more useful json representation.

The standard savegame location for the Steam release of the game is `<path\to\steam>\userdata\<user id>\1230530\remote`

### Requirements

The only thing needed is Python, 3.9 and 3.11 are tested. No extra packages need to be installed, even the `Windows embeddable package` variants of Python will do.
Either launch with the absolute path to python.exe, or add the directory of python.exe to the PATH variable.

### Usage

The game caches the savegame files in RAM, so the game may have to be restarted to load a modified file.

Note: The `compose` commands cannot overwrite the input file to help prevent accidents. Rename or copy the input file to another location first.

```
python savegame_body.py extract_raw <sav file in> <raw body out>
 -> Extracts the raw body from a save file.

python savegame_body.py extract_json <sav file in> <json body out> {options}
 -> Extracts the body from a save file as json.
 Options:
 --skip-era: Skips processing the game-specific portion of the save game body. May help with bugs or new game versions.
 --keep-inner-json-as-string: Will export the inner json as a raw string, to produce a 1:1 representation down to the characters.

python savegame_body.py compose_raw <sav file in> <raw body in> <sav file out> {options}
 -> Replaces the body in a save file from raw data.
 Options:
 --compress: Compresses the contents.

python savegame_body.py compose_json <sav file in> <json body in> <sav file out> {options}
 -> Replaces the body in a save file from a json representation.
 Options:
 --compress: Compresses the contents.
```

Using `extract_json` with `--keep-inner-json-as-string` and then `compose_json` with `--compress` can produce identical files down to the bit from the original. This depends on the compression library used in Python / CPython, but 3.9 and 3.11 appear to do just that.

## Stuff

See [format-docs.md](format-docs.md) for file format documentation.

The [name32table_hash.md](name32table_hash.md) script converts a raw dump of a string table (see the format docs) to a list of strings and their Name32 values. Useful to get an idea what certain values mean or can be replaced with.
