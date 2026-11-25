"""Command-line interface.

Typical uses::

    primedf book.pdf notes.pdf       # pages go to "book/" and "notes/" next to the PDFs
    primedf papers/                  # every PDF in a folder
    primedf book.pdf -o D:/calc/out  # explicit output folder
    primedf                          # no arguments: open the PrimeDF window
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .convert import (
    DEFAULT_WIDTH,
    ConversionError,
    convert_pdf,
    default_output_dir,
    find_pdfs,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="primedf",
        description="Convert PDF files into page images for the PrimeDF "
        "reader app on the HP Prime G2. Run without arguments to open the window.",
    )
    p.add_argument("pdfs", nargs="*", type=Path, metavar="PDF",
                   help="PDF file(s) or folders containing PDFs")
    p.add_argument("-o", "--out", type=Path, default=None,
                   help="output folder (default: a folder named after each PDF, next to it)")
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --help / --version / usage errors
        return exc.code if isinstance(exc.code, int) else 0

    if not args.pdfs:
        try:
            from .gui import run_gui
        except ImportError:  # Python built without tkinter
            parser.print_help()
            return 2
        return run_gui()

    pdfs = find_pdfs(args.pdfs)
    if not pdfs:
        print("primedf: no PDF files found in the given paths", file=sys.stderr)
        return 2
    if args.name and len(pdfs) > 1:
        print("primedf: --name only works with a single input file", file=sys.stderr)
        return 2

    failures = 0
    for pdf in pdfs:
        out_dir = args.out if args.out is not None else default_output_dir(pdf)

        def progress(done: int, total: int, _pdf: Path = pdf) -> None:
            if not args.quiet:
                print(f"\r{_pdf.name}: page {done}/{total}", end="", flush=True)

        try:
            result = convert_pdf(
                pdf, out_dir, name=args.name, width=args.width,
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
            print(f"\r{pdf.name}: {result.pages} pages -> {result.out_dir} "
                  f"({result.total_bytes / 1024:.0f} KiB)")
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
