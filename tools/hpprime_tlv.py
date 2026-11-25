#!/usr/bin/env python3
"""Inspect and build HP Prime app files (.hpapp / .hpappprgm / .hpappnote).

The format is undocumented. This tool encodes our reverse-engineered model
of it (see docs/HPAPPDIR_FORMAT.md) and *verifies* that model: ``check``
fails unless every byte is consumed by the record grammar and the file
serializes back to exactly the same bytes.

Usage:
    hpprime_tlv.py dump  FILE...                 pretty-print the record tree
    hpprime_tlv.py check FILE...                 parse + byte-exact round trip
    hpprime_tlv.py extract-program PRGM OUT      write the PPL source of an app program
    hpprime_tlv.py build-app --template DIR --program SRC [--icon PNG] --out DIR
                                                 make an importable .hpappdir
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

MAGIC = bytes.fromhex("7c618ab2")
HEADER_LEN = 12

T_FUNCTION = 0x3E
T_TEXT = 0x1B
SOURCE_TAG = 0x00C0009B  # type 0x1B (+flag), group 0x00, field 3: program source

TYPE_NAMES = {
    0x01: "rgb",
    0x03: "short?",
    0x05: "int",
    0x06: "complex?",
    0x08: "real",
    0x0B: "name",
    0x0E: "list",
    0x1B: "text",
    0x1E: "app",
    0x3E: "function",
}


class FormatError(Exception):
    pass


@dataclass
class Record:
    offset: int
    tag: int
    payload: bytes
    children: list[list[Record]] | None  # composite: elements, each a record list

    @property
    def type(self) -> int:
        return self.tag & 0x7F

    @property
    def group(self) -> int:
        return (self.tag >> 8) & 0xFF

    @property
    def field(self) -> int:
        return (self.tag >> 22) & 0x3FF

    @property
    def sub(self) -> int:
        return (self.tag >> 16) & 0x3F


@dataclass
class HPFile:
    header: bytes
    records: list[Record]

    @property
    def kind(self) -> int:
        return struct.unpack_from("<i", self.header, 4)[0]


def is_composite(type_byte: int) -> bool:
    return (type_byte & 0x0F) == 0x0E


def _u32(buf: bytes, pos: int) -> int:
    return struct.unpack_from("<I", buf, pos)[0]


# ------------------------------------------------------------------ reading
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
        payload = b"" if children is not None else buf[body + 4 : stop]
        records.append(Record(pos, tag, payload, children))
        pos = stop
    return records


def parse_file(data: bytes) -> HPFile:
    if data[:4] != MAGIC:
        raise FormatError("missing magic 7c 61 8a b2")
    if len(data) < HEADER_LEN:
        raise FormatError("file shorter than the 12-byte header")
    return HPFile(data[:HEADER_LEN], parse_records(data, HEADER_LEN, len(data)))


# ------------------------------------------------------------------ writing
def serialize(records: list[Record]) -> bytes:
    out = bytearray()
    for r in records:
        if r.children is not None:
            body = b"".join(
                struct.pack("<I", len(el)) + el for el in (serialize(e) for e in r.children)
            )
        else:
            body = r.payload
        out += struct.pack("<II", 4 + len(body), r.tag) + body
    return bytes(out)


def write_file(f: HPFile) -> bytes:
    return f.header + serialize(f.records)


# -------------------------------------------------------------- program text
def _main_function(f: HPFile) -> list[Record]:
    for r in f.records:
        if r.type == T_FUNCTION and r.children:
            return r.children[0]
    raise FormatError("no program function record (type 0x3E) found")


def get_program(f: HPFile) -> str | None:
    for r in _main_function(f):
        if r.tag == SOURCE_TAG:
            return r.payload.decode("utf-16-le").rstrip("\0")
    return None


def set_program(f: HPFile, source: str) -> None:
    """Store PPL ``source`` the way Connectivity Kit does: UTF-16LE, LF, NUL-terminated."""
    text = source.replace("\r\n", "\n").replace("\r", "\n")
    payload = text.encode("utf-16-le") + b"\0\0"
    element = _main_function(f)
    for r in element:
        if r.tag == SOURCE_TAG:
            r.payload = payload
            return
    element.append(Record(0, SOURCE_TAG, payload, None))


# ------------------------------------------------------------------ display
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
    if t == T_TEXT:
        text = p.decode("utf-16-le", "replace").rstrip("\0")
        head = text[:60].replace("\n", "\\n")
        return f"= {len(text)} chars: {head!r}{' ...' if len(text) > 60 else ''}"
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


# --------------------------------------------------------------- commands
def cmd_inspect(paths: list[str], show: bool) -> int:
    failed = False
    for name in paths:
        path = Path(name)
        data = path.read_bytes()
        if path.suffix == ".hpappnote":
            text = data.decode("utf-16-le", "replace").rstrip("\0")
            print(f"{path.name}: note, {len(data)} bytes, UTF-16LE text {text!r}")
            continue
        if path.suffix not in (".hpapp", ".hpappprgm"):
            print(f"{path.name}: app file, {len(data)} bytes (not a record file)")
            continue
        try:
            f = parse_file(data)
            if write_file(f) != data:
                raise FormatError("round trip changed the bytes")
        except FormatError as exc:
            print(f"{path.name}: FAILED: {exc}")
            failed = True
            continue
        print(f"{path.name}: {len(data)} bytes, header kind={f.kind}, "
              f"{len(f.records)} top-level records, parsed and round-tripped exactly")
        if show:
            dump(f.records)
    return 1 if failed else 0


def cmd_extract(prgm: str, out: str) -> int:
    source = get_program(parse_file(Path(prgm).read_bytes()))
    if source is None:
        print("this app has no program source", file=sys.stderr)
        return 1
    Path(out).write_text(source, encoding="utf-8", newline="\n")
    print(f"wrote {out} ({len(source)} characters)")
    return 0


def cmd_build(template: str, program: str, icon: str | None, out: str) -> int:
    src_dir, out_dir = Path(template), Path(out)
    prgms = list(src_dir.glob("*.hpappprgm"))
    if len(prgms) != 1:
        print(f"{src_dir}: expected exactly one .hpappprgm", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in src_dir.iterdir():
        if f.is_file() and f.suffix != ".hpappprgm":
            shutil.copyfile(f, out_dir / f.name)
    app = parse_file(prgms[0].read_bytes())
    set_program(app, Path(program).read_text(encoding="utf-8"))
    (out_dir / prgms[0].name).write_bytes(write_file(app))
    if icon:
        shutil.copyfile(icon, out_dir / "icon.png")
    print(f"built {out_dir}: " + ", ".join(sorted(p.name for p in out_dir.iterdir())))
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="hpprime_tlv.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("dump", "check"):
        sp = sub.add_parser(name)
        sp.add_argument("files", nargs="+")
    sp = sub.add_parser("extract-program")
    sp.add_argument("prgm")
    sp.add_argument("out")
    sp = sub.add_parser("build-app")
    sp.add_argument("--template", required=True, help="exported .hpappdir to start from")
    sp.add_argument("--program", required=True, help="PPL source file")
    sp.add_argument("--icon", help="PNG to install as icon.png (38x38)")
    sp.add_argument("--out", required=True, help="output .hpappdir folder")
    a = p.parse_args(argv[1:])
    if a.cmd in ("dump", "check"):
        return cmd_inspect(a.files, a.cmd == "dump")
    if a.cmd == "extract-program":
        return cmd_extract(a.prgm, a.out)
    return cmd_build(a.template, a.program, a.icon, a.out)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
