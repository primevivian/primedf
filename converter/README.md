# primedf (converter)

The PC-side half of [PrimeDF](../README.md). It rasterizes PDF pages into
`<doc>.<NNN>.png` images that the PrimeDF app on the HP Prime G2 displays.

## Standalone executable (recommended)

Download `primedf-windows-x64.exe`, `primedf-linux-x64` or
`primedf-macos-arm64` from the
[latest release](https://github.com/primevivian/primedf/releases/latest).
It needs no Python and nothing to install.

- **Drag and drop** PDFs onto the executable, or **double-click** it to pick
  files. The window stays open until you press Enter, and the output folder
  opens when the conversion finishes.
- **Terminal:** `primedf-windows-x64.exe book.pdf notes.pdf [options]`

## From source

```sh
pip install ./converter          # from the repository root
primedf book.pdf notes.pdf
```

## Options

| Option | Default | Meaning |
| --- | --- | --- |
| *(no PDFs)* | — | Opens a file picker |
| `-o, --out DIR` | `primedf_out` next to each PDF | Output folder |
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
pyinstaller --onefile --console --name primedf --collect-all pymupdf \
    --distpath dist --workpath build --specpath build \
    converter/packaging/primedf_entry.py
python converter/packaging/smoke_test.py dist/primedf.exe
```

CI (`.github/workflows/build.yml`) builds and smoke-tests all three platforms on
every converter change. Pushing a `v*` tag publishes them as a GitHub release
together with `PrimeDF.hpppl`.
