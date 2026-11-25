# PrimeDF

**A light, fast PDF reader for the HP Prime G2.**

PrimeDF lets you carry PDFs on your HP Prime G2 and read them with the touch
screen or the keypad. It has a plain file menu, smooth panning, and zoom.
It does nothing else.

> [!NOTE]
> **Status: 0.1.0, not yet verified on hardware.** The converter has an automated
> test suite. The calculator program follows the documented PPL APIs, but nobody
> has run it on a real G2 yet. Bug reports from real devices are very welcome.

## How it works

The HP Prime's programming language (PPL) can't read raw file bytes, so it can't
parse a PDF on the device. MicroPython on the Prime could in theory, but it would
need to decompress and lay out every page in an interpreter and render each font.
That would take seconds per page, the opposite of snappy.

PrimeDF splits the job in two:

```
  PC                                   HP Prime G2
 ┌────────────────────────┐            ┌──────────────────────────────┐
 │ primedf book.pdf       │  USB/CK    │ PrimeDF app                  │
 │  → book.001.png        │ ─────────▶ │  file menu → native PNG      │
 │  → book.002.png …      │            │  decode → hardware-speed     │
 └────────────────────────┘            │  scaled BLIT_P for pan/zoom  │
                                       └──────────────────────────────┘
```

1. **The converter** (`converter/`, Python) renders each PDF page once on your
   PC with MuPDF. It crops the margins and writes a compact grayscale PNG.
2. **The app** (`calculator/PrimeDF.hpppl`) lists the documents stored in its
   app files. It loads pages with the firmware's built-in PNG decoder and draws
   them with `BLIT_P`, which scales natively, so pan and zoom stay fast.

## Controls

| Action | Keys | Touch |
| --- | --- | --- |
| Pan | D-pad (tap = small step, hold = smooth accelerating scroll) | Drag with one finger |
| Zoom in / out | <kbd>+</kbd> / <kbd>−</kbd> | Pinch |
| Reset zoom (fit width) | — | Double-tap |
| Previous / next page | <kbd>LN</kbd> / <kbd>LOG</kbd> | — |
| Back to file menu | <kbd>Esc</kbd> | — |

In the file menu, use the arrows and <kbd>Enter</kbd>, or tap a document.
Press <kbd>Esc</kbd> to quit. The page number and zoom level appear briefly in
the bottom-right corner after each change.

## Quick start

**Requirements:** an HP Prime G2 (it should also run on a G1) on current firmware,
[HP Connectivity Kit](https://www.hpcalc.org/connectivity/), and Python 3.10+.

```sh
# 1. Convert your PDFs on the PC
pip install ./converter
primedf "My Book.pdf" lecture-notes.pdf -o out/
```

2. **Create the app once:** on the calculator, press <kbd>Apps</kbd>, highlight
   **Function**, tap **Save**, and name the copy `PrimeDF`.
3. **Install the program:** in Connectivity Kit, open
   *Application Library → PrimeDF → Program*. Replace its contents with
   [`calculator/PrimeDF.hpppl`](calculator/PrimeDF.hpppl) and save.
4. **Copy the documents:** drag the `.png` files from `out/` onto the **PrimeDF**
   app in Connectivity Kit's calculator tree.
5. On the calculator, open **PrimeDF** from the Apps library. Choose **Start** if
   the menu doesn't appear right away.

[`docs/INSTALL.md`](docs/INSTALL.md) has the step-by-step guide with
troubleshooting.

## Tips

- **Text too small at fit width?** That's normal on a 320×240 screen. Press
  <kbd>+</kbd> three times (≈ 2×) for comfortable reading. The zoom level stays
  the same when you turn pages.
- **Want crisper zoom?** Convert with `-w 960`. Files get bigger and pages load
  more slowly.
- **Storage:** a typical text page is 30–80 KB at the default width.

## Repository layout

```
calculator/PrimeDF.hpppl   the HP Prime app program (HP PPL)
converter/                 the PC converter (Python package + tests)
docs/INSTALL.md            detailed setup and troubleshooting
docs/DESIGN.md             architecture, file format, performance notes
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Hardware test reports are the most
useful contribution right now.

## License

[MIT](LICENSE)
