As of 2023-08-12 (release build)[cite: 3]

`Atlas Fallen/build_info`: `* Era - PC 110045 (SVN) / 1691132679 (Git) / 643 - Fri Aug 04 09:49:21 2023`[cite: 3]

le/be: Little/Big Endian[cite: 3]

## Base Header
Absolute position: 0[cite: 3]

- +0: uint32_t le magic - for Atlas Fallen 0x7A145F28[cite: 3]
- +4: uint32_t le checksum - over the decompressed Body (see section below for algorithm)[cite: 3]
- +8: uint32_t le header_size[cite: 3]

## Header (metadata)
Absolute position: 0xC. Length seemingly hardcoded in engine to 0xD0.[cite: 3]

- +0: uint32_t le fledge_body_format - body file format, known 0x29[cite: 3]

Other fields not analyzed so far. Appears to contain Name32 fields for[cite: 3]

## Body block header
Absolute position: sizeof(BaseHeader) + BaseHeader.header_size[cite: 3]

- +0: bool is_compressed, stored as uint32_t le[cite: 3]
- +4: uint32_t le compressed_size[cite: 3]
- +8: uint32_t le decompressed_size[cite: 3]

Followed by Body, either raw (`decompressed_size` bytes) or Deflate compressed (`compressed_size` bytes), indicated by `is_compressed`.[cite: 3]

## Body

The Body uses _big endian_ encoding for all fields. See the section below for the encoding of the data types.[cite: 3]

(Fledge::Core::SaveGameDesc)[cite: 3]

- `Name32`[cite: 3]
- `Name32`[cite: 3]
- `string` (known: "ERA-Savegame")[cite: 3]
- `uint32_t` core_body_format - known value 2[cite: 3]
- `uint8_t`[cite: 3]
- `uint64_t`[cite: 3]
- if core_body_format < 1: `uint16_t`[cite: 3]
- `bool`[cite: 3]
- if core_body_format >= 2: `uint32_t` some\_field1[cite: 3]
- `uint32_t` sizevar_1[cite: 3]
- for i in range(sizevar_1): {`uint64_t`, `bool`}[cite: 3]
- `uint32_t` num_running_conversations[cite: 3]
- for i in range(num_running_conversations): {`Name32`, `int32_t`}[cite: 3]
- `uint32_t` sizevar_3[cite: 3]
- for i in range(sizevar_3): {`Name32`, `bool`}[cite: 3]
- `uint32_t` json_string_size[cite: 3]
- `binary`, size given by json_string_size.[cite: 3]

(Era::SaveGameDesc)[cite: 3]

- (all of the above)[cite: 3]
- `binary`, size 0x60[cite: 3]
- `uint32_t` sizevar_4[cite: 3]
- for i in range(sizevar_4): {`uint64_t`, `uint8_t`}[cite: 3]
- `uint32_t` sizevar_5[cite: 3]
- for i in range(sizevar_5): {`Name32`, for k in range(0x10000): `uint32_t`}[cite: 3]
  - data appears to be a raw image; example values for the Name32 field: `hash("__default")=0x2db22441`, `hash("ui_map_lvl2")=0x4f4f451e`[cite: 3]
- `Name32` - example: `hash("ui_map_lvl2")=0x4f4f451e`[cite: 3]
- `vec3` player position(?)[cite: 3]
- `float`[cite: 3]
- `bool` boolvar1[cite: 3]
- `bool` boolvar2[cite: 3]
- `bool` boolvar3[cite: 3]
- `bool` boolvar4[cite: 3]
- `bool` boolvar5[cite: 3]
- if (header.fledge_body_format >= 0x27) `bool` boolvar6[cite: 3]
- if (header.fledge_body_format >= 0x28) `bool` boolvar7[cite: 3]
- if (header.fledge_body_format >= 0x28) `bool` boolvar8[cite: 3]
- if (header.fledge_body_format >= 0x28) `bool` boolvar9[cite: 3]
- if (header.fledge_body_format >= 0x28) `bool` boolvar10[cite: 3]
- `bool` boolvar11[cite: 3]
- `bool` boolvar12[cite: 3]
- `uint8_t`[cite: 3]
- `bool` boolvar13[cite: 3]
- `uint8_t`[cite: 3]
- `bool` boolvar14[cite: 3]
- `uint8_t`[cite: 3]
- if (header.fledge_body_format >= 0x28) `int32_t`[cite: 3]
- if (header.fledge_body_format < 0x29) `uint32_t` - apparently moved since format 0x29, same as some\_field1 in core_body_format >= 2[cite: 3]
- `uint32_t` sizevar_6[cite: 3]
- for i in range(sizevar_6): `uint32_t`[cite: 3]
- `uint32_t` sizevar_7[cite: 3]
- for i in range(sizevar_7): `uint32_t`[cite: 3]
- if (header.fledge_body_format >= 0x18):[cite: 3]
  - `uint32_t` sizevar_8[cite: 3]
  - for i in range(sizevar_8): `Name32`[cite: 3]
- `uint32_t` sizevar_9[cite: 3]
- `binary`, size from sizevar_9[cite: 3]
- if (header.fledge_body_format >= 0x1B):[cite: 3]
  - `uint32_t` sizevar_10[cite: 3]
  - for i in range(sizevar_10): `Name32`[cite: 3]
- if (header.fledge_body_format >= 0x25):[cite: 3]
  - `uint32_t` global_mapdata1[cite: 3]
  - `uint32_t` global_mapdata_count[cite: 3]
  - for i in range(global_mapdata_count):[cite: 3]
    - `uint8_t`[cite: 3]
    - `uint8_t`[cite: 3]
    - `Variant`[cite: 3]
    - `Variant`[cite: 3]
    - `Variant`[cite: 3]
    - `vec<3>`[cite: 3]

### Data types

- Variant[cite: 3]
  - 4 byte uint32_t - variant type[cite: 3]
    ```
	switch (type) { //each variant type is encoded as specified in the data types list
	  case 1: bool
	  case 2: int32_t
	  case 3: int8_t
	  case 4: uint8_t
	  case 5: uint16_t
	  case 6: uint32_t
	  case 7: uint64_t
	  case 8: float
	  case 9: Degree
	  case 10: Radian
	  case 11: vec<2>
	  case 12: vec<3>
	  case 13: vec<4>
	  case 14: Color
	  case 15: Rotate
	  case 16: quat
	  case 17: UDim
	  case 18: UVector2
	  case 19: Rect
	  case 20: Name32
	  case 21: Ref
	  case 22: (none) //unsure if void or null
	  case 23: Variant array - `uint32_t` count, for i in range(count): `Variant`
	  case 24: Variant dictionary - `uint32_t` count, for i in range(count): `Name32`, `Variant`
	  case 25: Curve
	  default: //void
	}
    ```
- Ref[cite: 3]
  - `uint32_t`[cite: 3]
  - `uint64_t`[cite: 3]
  - `bool`[cite: 3]
  - if (\<unknown condition\>) `string`[cite: 3]
- Curve[cite: 3]
  - `uint32_t` count[cite: 3]
  - for i in range(count): `float`, `vec<2>`, `vec<2>`, `vec<2>`[cite: 3]
- Rect[cite: 3]
  - 2x `uint16_t`[cite: 3]
- Color[cite: 3]
  - 4x `float`[cite: 3]
- Degree[cite: 3]
  - `float`[cite: 3]
- Radian[cite: 3]
  - `float`[cite: 3]
- Rotate[cite: 3]
  - 3x `Radian`[cite: 3]
- quat[cite: 3]
  - 4x `float`[cite: 3]
- int32_t (4 bytes, be)[cite: 3]
- bool (4 bytes (! unlike uint8_t), be) - 0x00000000 (false) or 0x00000001 (true)[cite: 3]
- float (4 bytes, be)[cite: 3]
- UDim[cite: 3]
  - 2x `float`[cite: 3]
- UVector2[cite: 3]
  - 2x `UDim`[cite: 3]
- vec<2>[cite: 3]
  - 2x `float`[cite: 3]
- vec<3>[cite: 3]
  - 3x `float`[cite: 3]
- vec<4>[cite: 3]
  - 4x `float`[cite: 3]
- Name32[cite: 3]
  - `uint32_t` - name hash[cite: 3]
  - 4 byte - unknown, always 0(?), may be padding or reserved[cite: 3]
  - `bool` (i.e. 4 byte) - unknown[cite: 3]
- string[cite: 3]
  - `uint32_t` len_and_flag = len | 0x80000000 - len always padded to a multiple of 4 bytes (regardless of position in stream)[cite: 3]
  - \<raw text data of given len\> - padding with 00 bytes[cite: 3]
- uint64_t (8 bytes, be)[cite: 3]
- uint32_t (4 bytes, be)[cite: 3]
- uint16_t (2 bytes, be)[cite: 3]
- uint8_t (1 byte)[cite: 3]
- int8_t (1 byte)[cite: 3]
- binary (no length field; length padded to multiple of 4 bytes, regardless of position in stream)[cite: 3]

## Checksum, Name32 hash algorithm
```python
def compute_checksum(data):
    # Matches 'sdbm' ([http://www.cse.yorku.ca/~oz/hash.html#sdbm](http://www.cse.yorku.ca/~oz/hash.html#sdbm))
    sum = 0
    for i in range(len(data)):
        sum = ((sum*0x1003F)&0xFFFFFFFF) + data[i]
        sum = sum&0xFFFFFFFF
    return sum
```[cite: 3]

## Name32 lookup
The game has an internal lookup to convert from strings to Name32 hashes. Can be dumped from game memory, but appears to be incomplete.[cite: 3]

Memory search for: `44 45 46 41 55 4C 54 00 55 4E 44 45 46 49 4E 45 44 00 4C 65 66 74 00 43 65 6E 74 65 72 00 52 69 67 68 74 00 4A 75 73 74 69 66 79 00 4E 6F 6E 65 00`
Contains a string table (> 3 MiB), each string separated by a '\0' character.[cite: 3]

---

## Format 0x64 Update & Current Status (Reign of Sand / Modern Builds)

### Supported Era Formats
* **Legacy Formats:** `0x00` through `0x29` (Original release builds).
* **Updated Formats:** Added full extraction and repacking support for **`0x64`** (100 in decimal), used in newer game updates (e.g., *Reign of Sand*).

### Structural Changes Discovered in Format `0x64`
1. **New Extra Padding/Data Block (`fieldEra_format0x64_extra`):**
   * Inserted immediately after `fieldEra50` (`float`) and before `bool fieldEra60`.
   * Consists of a block of up to **164 32-bit DWORDs** (`0x290` bytes, commonly padded with `0xFFFFFFFF`).
2. **Dynamic Map Images (`fieldEra20`):**
   * Map image data no longer strictly adheres to the legacy fixed `0x10000` (`262,144` bytes) block size; format `0x64` uses variable/dynamic byte lengths or empty buffers, requiring bounds-checked reads to prevent false-positive 256KB allocations.
3. **`Name32` Third-DWORD Sentinel Values:**
   * In legacy builds (`<= 0x29`), the third 4-byte field of a `Name32` struct acted as a strict boolean (`0` or `1`). In format `0x64`, uninitialized or sentinel `Name32` entries (such as `fieldEra30_ui_map_type`) populate this field with `0xFFFFFFFF`.
4. **Packed Flag Fields (`fieldEra100` – `fieldEra220`):**
   * Following `fieldEra90`, the subsequent flag/boolean sequence is packed or contains non-boolean values (e.g., `0x00000101` / `257`), requiring them to be serialized/deserialized as raw `uint32_t` fields rather than strict `[0, 1]` booleans.

### Current Status
* **Extraction (`extract_json` / `extract_raw`) & Repacking (`compose_json` / `compose_raw`):** Working end-to-end on format `0x64` save files with full bounds checking, missing-key fallback protection during JSON composition, and automatic `sdbm` checksum recalculation.
* **Next Steps / Pending Investigation:**
  * Identify the specific gameplay meaning of the individual DWORDs inside the 164-DWORD `fieldEra_format0x64_extra` block and the packed `fieldEra100`–`fieldEra220` flags.
  * Verify whether intermediate formats between `0x2A` and `0x63` exist across other patches/platforms and share the `0x64` layout.