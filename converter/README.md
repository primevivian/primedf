# primedf (converter)

The PC-side half of [PrimeDF](../README.md). It rasterizes PDF pages into
`<doc>.<NNN>.png` images that the PrimeDF app on the HP Prime G2 displays.

## Standalone executable (recommended)

Download from the
[latest release](https://github.com/primevivian/primedf/releases/latest).
You need no Python and nothing to install.

- **Windows: `PrimeDF-windows-x64.exe`** is a small window. Drop PDFs (or
  folders) into it, or click to pick files. Dropping them onto the `.exe` icon
  works too. **Open folder** shows the result.
- **Linux / macOS: `primedf-linux-x64`, `primedf-macos-arm64`** are
  command-line tools that take the options below. Run them without arguments
  to open the window.

The Windows build is about 15 MB. It bundles Python, Tk for the window, and
PDFium (Chrome's PDF engine) as a single small native library. It needs no
imaging library because PNGs are written by `primedf/png.py`.

## From source

```sh
pip install ./converter          # from the repository root
primedf book.pdf notes.pdf
```

## Options

| Option | Default | Meaning |
| --- | --- | --- |
| *(no PDFs)* | — | Opens the converter window |
| `PDF ...` | — | PDF files, or folders containing PDFs |
| `-o, --out DIR` | a folder named after each PDF, next to it | Output folder |
| `-n, --name NAME` | file name | Name shown in the calculator menu (single input only) |
| `-w, --width PX` | `640` | Pixel width of a typical page's content. 640 gives readable text at 2x fit-width. Use larger values for sharper zoom (bigger files, slower page loads). |
| `--no-trim` | off | Keep page margins (by default each page is cropped to its content) |
| `--rgb` | off | Write color PNGs instead of grayscale |
| `--password PW` | — | Password for encrypted PDFs |
| `-q, --quiet` | off | Only print errors |

Names are reduced to ASCII letters, digits and `_`, max 16 characters.
Documents are limited to 999 pages. If you need more, split the PDF.

## Development

```sh
cd converter
pip install -e ".[dev]"
ruff check .
pytest
```

### Building the executable locally

```sh
pip install ./converter pyinstaller
python converter/packaging/make_icon.py build/primedf.ico
pyinstaller --onefile --windowed --name PrimeDF --icon build/primedf.ico \
    --collect-all pypdfium2 --collect-all pypdfium2_raw \
    converter/packaging/primedf_gui_entry.py
pip install PyMuPDF   # only to generate the smoke-test PDF
python converter/packaging/smoke_test.py dist/PrimeDF.exe --gui-selftest
```

CI (`.github/workflows/build.yml`) builds and smoke-tests all three platforms on
every converter change. Pushing a `v*` tag publishes them as a GitHub release
together with `PrimeDF.hpppl`.
