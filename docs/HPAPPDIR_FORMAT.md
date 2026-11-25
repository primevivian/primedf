# The HP Prime `.hpappdir` format (reverse-engineered)

HP doesn't publish the format of the app packages that HP Connectivity Kit
imports and exports. These notes are PrimeDF's own reverse-engineering. They
come from real exports, kept in [`format-samples/`](format-samples/), and
are checked by [`tools/hpprime_tlv.py`](../tools/hpprime_tlv.py). CI runs
that tool on every sample, and it fails unless every byte parses under the
model below.

Each statement is labeled by how sure we are:

- **Confirmed**: every sample matches, and decoded values equal known
  defaults.
- **Observed**: seen in the samples, meaning unclear.
- **Hypothesis**: plausible, not yet tested.

Firmware and tools used: HP Prime G2, current firmware (2.1.x), and the HP
Connectivity Kit for Windows.

---

## 1. Package layout

An app is a folder named `<NAME>.hpappdir`. Connectivity Kit exports it, and
you can drag it back onto *Application Library* to import it.

```
PRIMEDF.hpappdir/
├── PRIMEDF.hpapp        app state (binary, record tree)
├── PRIMEDF.hpappprgm    app program (binary, record tree)
└── PRIMEDF.hpappnote    app note (UTF-16LE text)
```

- **Confirmed:** the exported names are in upper case (`PRIMEDF`) even
  though the app was saved as `PrimeDF`.
- **Hypothesis:** any other file in the folder is one of the app's files
  (`AFiles`). That's how PrimeDF stores its page images. Sample 03 (see §6)
  will confirm it.
- **Hypothesis (community reports):** a file named `icon.png` (or `icon.jpg`)
  becomes the app's icon in the Apps library. Forum posts cite 38×38 px and
  say Connectivity Kit scales pictures to 38×38. One report says the icon only
  appears after the app is edited and saved once on the calculator. PrimeDF
  ships a 38×38 `icon.png`; hardware confirmation is pending.

## 2. `.hpappnote`

- **Confirmed:** UTF-16LE text, NUL-terminated. An empty note is the two bytes
  `00 00`. It has no header or magic number.

## 3. Binary files (`.hpapp`, `.hpappprgm`)

### 3.1 Header (12 bytes)

| Offset | Size | Value | Meaning |
| --- | --- | --- | --- |
| 0 | 4 | `7C 61 8A B2` | magic (**confirmed**, same in both files) |
| 4 | 4 | i32 LE | file kind (**observed**): `-1` in `.hpapp`, `-2` in `.hpappprgm` |
| 8 | 4 | u32 LE | **observed**: `0x00600060` in `.hpapp`, `0` in `.hpappprgm` |

The rest of the file is a sequence of records, up to the last byte.

### 3.2 Records (confirmed)

All integers are little-endian.

```
record  := size:u32  tag:u32  payload[size - 4]
```

`size` counts the tag plus the payload. It doesn't count itself.

The tag is 4 bytes:

| Byte(s) | Meaning |
| --- | --- |
| 0, bits 0–6 | **type** (§3.3) |
| 0, bit 7 | flag, **observed** on many records, meaning unknown |
| 1 | **group**: an object or namespace id (**observed**, for example `0x97` for the plot range and `0x65` for function entries) |
| 2–3 | u16. The low 6 bits are a sub-id (**observed** as `0x3F` on the file-level settings, otherwise `0`). The high 10 bits are the **field index**, starting at 1 and in increasing order within a parent. |

### 3.3 Types

| Type | Payload | Status |
| --- | --- | --- |
| `0x0E`, `0x1E`, `0x3E` (low nibble `E`) | **composite**: a sequence of *elements*, each `el_size:u32` followed by `el_size` bytes of nested records. An element can be empty (`el_size = 0`). | structure **confirmed** |
| `0x05` | integer, `size - 4` bytes, signed LE (4 or 8 bytes seen) | **confirmed** |
| `0x08` | real number, 8 bytes, BCD (§3.4) | **confirmed** |
| `0x0B` | name: UTF-16LE in a fixed 64-byte (32-character) NUL-padded buffer | **confirmed** |
| `0x1B` | text: variable-length UTF-16LE, NUL-terminated (`size - 4` bytes). Used for program source. | **confirmed** (sample 02) |
| `0x01` | 3 bytes `RR GG BB` color | **confirmed** (the ten default function colors) |
| `0x03` | 2 bytes | **observed** |
| `0x06` | 16 bytes, all `FF` in the samples | **observed**. Possibly "undefined" or a complex value. |

The variants seen of the composite type are `0x0E` (list), `0x1E` (the
top-level app object in `.hpapp`) and `0x3E` (a function entry in
`.hpappprgm`). Some `0x08` records hold values that aren't valid BCD reals.
See §5.

### 3.4 Real numbers (confirmed)

Take the 8 payload bytes as a u64 LE and read its 16 hex nibbles from the
top:

```
nibble 0       sign: 0 = +, 9 = −
nibbles 1–12   12 BCD mantissa digits, d.ddddddddddd
nibbles 13–15  3 BCD exponent digits
```

Examples from the samples:

| Bytes | u64 | Value |
| --- | --- | --- |
| `01 00 00 00 00 00 59 91` | `9159000000000001` | −1.59 × 10¹ = **−15.9** |
| `01 00 00 00 00 00 59 01` | `0159000000000001` | **15.9** |
| `00 00 00 00 00 00 00 02` | `0200000000000000` | **2** |

These match the Prime's 12 significant digits. **Hypothesis:** negative
exponents are stored as a 1000-complement (999 = −1). None appear in the
samples yet.

## 4. What the samples contain

### 4.1 `.hpapp` of a copy of the Function app (sample 01)

```
7 file-level ints        group 0xFF, sub 0x3F, fields 1..7       (meaning unknown)
app (0x1E)               group 0xFC
├─ plot setup            group 0x98
│  ├─ X range            group 0x97: Xmin −15.9, Xmax 15.9       (confirmed)
│  ├─ Y range            group 0x97: Ymin −10.9, Ymax 10.9       (confirmed)
│  ├─ int 269            (unknown; maybe flags)
│  ├─ (2, 2)             group 0x96: X tick spacing?             (Function default: 2)
│  ├─ (1, 1)             group 0x96: Y tick spacing?             (Function default: 1)
│  └─ group 0x9A         name '', two non-BCD 0x08 fields, real 75, short
├─ symbolic view         group 0x67 → 0x66: list of 10 entries   (F1..F9, F0)
│  └─ each (0x65)        int 2, color RGB, empty expression list
│                        colors: 0000FF FF0000 008000 FFA500 800080
│                                FF00FF 00FF00 000080 800000 FFD700  (confirmed)
├─ 5 reals = 0           group 0x67
└─ group 0x9A/0x99       reals and settings (some non-BCD)
```

### 4.2 `.hpappprgm` with no program (sample 01)

```
3 file-level ints        group 0xFF, sub 0x3F (fields 1, 8, 2) = 0
function (0x3E)          name 'Main', int 0
list of 10 entries       each: empty name, 16 bytes of FF
```

**There's no PPL source in this sample.** The app was exported before a
program was pasted in.

### 4.3 `.hpappprgm` with a program (sample 02, confirmed)

Pasting the PrimeDF program in Connectivity Kit changes exactly one thing:
the `Main` function record gets a **third field**, a text record (`0x1B`)
with tag `9B 00 C0 00` (group 0, field 3) that holds the **plain source code**.

```
function (0x3E)          group 0x00, field 5
└─ element
   ├─ name   0x8B  field 1   'Main'
   ├─ int    0x85  field 2   0
   └─ text   0x9B  field 3   the whole PPL program            <- new
```

- The source is stored **verbatim**: UTF-16LE, LF line endings, and a final
  NUL character (`00 00`). Decoded, it matched `calculator/PrimeDF.hpppl`
  byte for byte, apart from the repo file's CRLF line endings.
- **No compiled code is stored.** The calculator compiles the source itself.
- The header, the file-level ints and the 10-slot list are unchanged.
- Sizes are recomputed up the tree: the function record grows by the text
  record's size, and so does its element.
- In `.hpapp`, only one byte changed: the high half of file-level int 7 went
  from `0x12` to `0x11` (meaning unknown). Everything else is identical.

**Verified by construction.** `hpprime_tlv.py build-app` inserts the source
from sample 02 into sample 01's program file. CI checks that the result is
identical to sample 02's `.hpappprgm`, so our writer produces exactly what
Connectivity Kit does. PrimeDF's release package is built this way, from
`calculator/app-template/` and the current program.

## 5. Open questions

1. ~~Where the program source lives.~~ Answered by sample 02 (§4.3).
2. **App files.** Are they plain files in the folder (likely), and is
   `icon.png` used as the app icon? → sample 03
3. The meaning of the header's `extra` word, the file-level ints (group
   `0xFF`), the tag flag bit, and the non-BCD `0x08` payloads (for example
   `ff 0f 00 00 00 00 00 01`, and `...40` as the top byte).
4. What the 10 empty `(name, FF×16)` slots in `.hpappprgm` are. Their count
   matches F1–F9/F0, but they're in the program file.

## 6. Adding a sample

Export with Connectivity Kit: drag the app from *Application Library* to a
folder. Add the export under `docs/format-samples/NN-short-description/`,
with a line in the table below describing exactly what was done on the
calculator. CI parses it automatically. Then dump it:

```sh
python3 tools/hpprime_tlv.py dump docs/format-samples/NN-*/*.hpappdir/*
```

| # | Folder | How it was made |
| --- | --- | --- |
| 01 | `01-function-copy-no-program` | Apps → Function → Save as `PrimeDF`. No program, no files. |
| 02 | `02-with-program` | Sample 01 plus the PrimeDF program (v0.2.0) pasted in Connectivity Kit and saved. |
| 03 | *(wanted)* | Sample 02 plus one page image (`test.001.png`) added to the app's files |

A minimal change between two samples makes the diff easy to read. Compare
the dumps of two samples to see what one action changed.
