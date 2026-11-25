"""Minimal PNG encoder (stdlib only).

PrimeDF only needs to *write* simple 8-bit PNGs, so it doesn't need an imaging
library. Rows go in as raw bytes, and filter type 0 plus zlib level 9 compress
mostly-white document pages well.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Sequence

PNG_GRAY = 0
PNG_RGB = 2
PNG_RGBA = 6

_CHANNELS = {PNG_GRAY: 1, PNG_RGB: 3, PNG_RGBA: 4}
_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def encode_png(rows: Sequence[bytes], width: int, height: int, color_type: int,
               level: int = 9) -> bytes:
    """Encode 8-bit ``rows`` (top to bottom) as a PNG file."""
    if color_type not in _CHANNELS:
        raise ValueError(f"unsupported color type {color_type}")
    if width <= 0 or height <= 0 or len(rows) != height:
        raise ValueError("rows do not match the image size")
    row_len = width * _CHANNELS[color_type]
    if any(len(r) != row_len for r in rows):
        raise ValueError(f"every row must be {row_len} bytes")
    raw = b"".join(b"\x00" + bytes(r) for r in rows)  # filter type 0 per row
    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return (_SIGNATURE + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw, level))
            + _chunk(b"IEND", b""))


def read_png_header(data: bytes) -> tuple[int, int, int]:
    """Return ``(width, height, color_type)`` of a PNG (used by tests and tools)."""
    if data[:8] != _SIGNATURE or data[12:16] != b"IHDR":
        raise ValueError("not a PNG file")
    width, height, _depth, color_type = struct.unpack(">IIBB", data[16:26])
    return width, height, color_type
