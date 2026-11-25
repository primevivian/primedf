"""Command-line interface: ``primedf book.pdf [more.pdf ...] -o out/``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .convert import DEFAULT_WIDTH, ConversionError, convert_pdf


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="primedf",
        description="Convert PDF files into page images for the PrimeDF "
        "reader app on the HP Prime G2.",
    )
    p.add_argument("pdfs", nargs="+", type=Path, metavar="PDF",
                   help="PDF file(s) to convert")
    p.add_argument("-o", "--out", type=Path, default=Path("primedf_out"),
                   help="output folder (default: ./primedf_out)")
    p.add_argument("-n", "--name",
                   help="document name shown on the calculator "
                   "(single input only; default: the file name)")
    p.add_argument("-w", "--width", type=int, default=DEFAULT_WIDTH,
                   help=f"page content width in pixels (default: {DEFAULT_WIDTH}; "
                   "larger = sharper zoom, bigger files)")
    p.add_argument("--no-trim", action="store_true",
                   help="keep the page margins instead of cropping to content")
    p.add_argument("--rgb", action="store_true",
                   help="write color PNGs instead of grayscale")
    p.add_argument("--password", help="password for encrypted PDFs")
    p.add_argument("-q", "--quiet", action="store_true", help="only print errors")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.name and len(args.pdfs) > 1:
        print("primedf: --name only works with a single input file", file=sys.stderr)
        return 2

    failures = 0
    for pdf in args.pdfs:
        def progress(done: int, total: int, _pdf: Path = pdf) -> None:
            if not args.quiet:
                print(f"\r{_pdf.name}: page {done}/{total}", end="", flush=True)

        try:
            result = convert_pdf(
                pdf, args.out, name=args.name, width=args.width,
                trim=not args.no_trim, rgb=args.rgb, password=args.password,
                progress=progress,
            )
        except ConversionError as exc:
            if not args.quiet:
                print()
            print(f"primedf: {exc}", file=sys.stderr)
            failures += 1
            continue
        if not args.quiet:
            print(f"\r{pdf.name}: {result.pages} pages -> "
                  f"{args.out / (result.name + '.*.png')} "
                  f"({result.total_bytes / 1024:.0f} KiB)")
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
