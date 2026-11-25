# primedf (converter)

The PC-side half of [PrimeDF](../README.md). It rasterizes PDF pages into
`<doc>.<NNN>.png` images that the PrimeDF app on the HP Prime G2 displays.

```sh
pip install ./converter          # from the repository root
primedf book.pdf notes.pdf -o out/
```

| Option | Default | Meaning |
| --- | --- | --- |
| `-o, --out DIR` | `primedf_out` | Output folder |
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
