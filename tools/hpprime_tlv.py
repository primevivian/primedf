#!/usr/bin/env python3
"""Inspect HP Prime app files (.hpapp / .hpappprgm / .hpappnote).

The format is undocumented. This tool encodes our reverse-engineered model
of it (see docs/HPAPPDIR_FORMAT.md) and *verifies* that model: ``check``
fails unless every byte of the file is consumed exactly by the record
grammar.

Usage:
    hpprime_tlv.py dump  FILE...   pretty-print the record tree
    hpprime_tlv.py check FILE...   verify the files parse completely (exit 1 if not)
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass
from pathlib import Path

MAGIC = bytes.fromhex("7c618ab2")
HEADER_LEN = 12

TYPE_NAMES = {
    0x01: "rgb?",
    0x03: "short?",
    0x05: "int",
    0x06: "complex?",
    0x08: "real",
    0x0B: "string",
    0x0E: "list",
    0x1E: "app",
    0x3E: "function",
}


class FormatError(Exception):
    pass


@dataclass
class Record:
    offset: int
    size: int
    tag: int
    payload: bytes
    children: list[list[Record]] | None  # composite: elements, each a record list

    @property
    def type(self) -> int:
        return self.tag & 0x7F

    @property
    def flag(self) -> bool:
        return bool(self.tag & 0x80)

    @property
    def group(self) -> int:
        return (self.tag >> 8) & 0xFF

    @property
    def field(self) -> int:
        return (self.tag >> 22) & 0x3FF

    @property
    def sub(self) -> int:
        return (self.tag >> 16) & 0x3F


def is_composite(type_byte: int) -> bool:
    return (type_byte & 0x0F) == 0x0E


def _u32(buf: bytes, pos: int) -> int:
    return struct.unpack_from("<I", buf, pos)[0]


def parse_records(buf: bytes, start: int, end: int) -> list[Record]:
    records = []
    pos = start
    while pos < end:
        if pos + 4 > end:
            raise FormatError(f"truncated size field at {pos:#x}")
        size = _u32(buf, pos)
        body, stop = pos + 4, pos + 4 + size
        if size < 4 or stop > end:
            raise FormatError(f"bad record size {size} at {pos:#x} (container ends {end:#x})")
        tag = _u32(buf, body)
        children = None
        if is_composite(tag & 0xFF):
            children = []
            p = body + 4
            while p < stop:
                if p + 4 > stop:
                    raise FormatError(f"truncated element size at {p:#x}")
                el_size = _u32(buf, p)
                if p + 4 + el_size > stop:
                    raise FormatError(f"element of {el_size} bytes at {p:#x} overruns record")
                children.append(parse_records(buf, p + 4, p + 4 + el_size))
                p += 4 + el_size
        records.append(Record(pos, size, tag, buf[body + 4 : stop], children))
        pos = stop
    return records


def parse_file(data: bytes) -> tuple[tuple[int, int], list[Record]]:
    if data[:4] != MAGIC:
        raise FormatError("missing magic 7c 61 8a b2")
    if len(data) < HEADER_LEN:
        raise FormatError("file shorter than the 12-byte header")
    kind, extra = struct.unpack_from("<iI", data, 4)
    return (kind, extra), parse_records(data, HEADER_LEN, len(data))


def decode_real(payload: bytes) -> float | None:
    """8 bytes, u64 LE; nibbles from the top: sign, 12 BCD digits, 3 BCD exponent."""
    if len(payload) != 8:
        return None
    nib = f"{int.from_bytes(payload, 'little'):016x}"
    sign, mant, exp = nib[0], nib[1:13], nib[13:]
    if sign not in "09" or not (mant + exp).isdigit():
        return None
    e = int(exp)
    if e >= 500:  # assumed 1000-complement for negative exponents
        e -= 1000
    value = float(f"{mant[0]}.{mant[1:]}e{e}")
    return -value if sign == "9" else value


def describe(rec: Record) -> str:
    t, p = rec.type, rec.payload
    if rec.children is not None:
        return f"{len(rec.children)} element(s)"
    if t == 0x05:
        return f"= {int.from_bytes(p, 'little', signed=True)}"
    if t == 0x08:
        r = decode_real(p)
        if r is not None:
            return f"= {r:g}"
    if t == 0x0B:
        return f"= {p.decode('utf-16-le', 'replace').rstrip(chr(0))!r}"
    shown = p[:24].hex(" ")
    return f"= {shown}{' ...' if len(p) > 24 else ''}"


def dump(records: list[Record], indent: int = 1) -> None:
    pad = "  " * indent
    for r in records:
        name = TYPE_NAMES.get(r.type, "?")
        print(f"{pad}@{r.offset:#06x} type={r.tag & 0xFF:#04x} ({name}) grp={r.group:#04x} "
              f"field={r.field} sub={r.sub:#04x}  {describe(r)}")
        for i, element in enumerate(r.children or []):
            print(f"{pad}  [{i}]" + ("" if element else " (empty)"))
            dump(element, indent + 2)


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in ("dump", "check"):
        print(__doc__, file=sys.stderr)
        return 2
    failed = False
    for name in argv[2:]:
        path = Path(name)
        data = path.read_bytes()
        if path.suffix == ".hpappnote":
            text = data.decode("utf-16-le", "replace").rstrip("\0")
            print(f"{path.name}: note, {len(data)} bytes, UTF-16LE text {text!r}")
            continue
        try:
            (kind, extra), records = parse_file(data)
        except FormatError as exc:
            print(f"{path.name}: FAILED: {exc}")
            failed = True
            continue
        print(f"{path.name}: {len(data)} bytes, header kind={kind} extra={extra:#010x}, "
              f"{len(records)} top-level records, fully parsed")
        if argv[1] == "dump":
            dump(records)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
