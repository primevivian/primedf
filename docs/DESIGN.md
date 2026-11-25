# PrimeDF design notes

## Goals

1. Open documents stored on the calculator and read them.
2. Keep it fast. Every interaction should feel instant on a 528 MHz HP Prime G2.
3. Add nothing else.

## Why pre-rasterize?

| Approach | Verdict |
| --- | --- |
| Parse PDFs in PPL | Impossible. PPL has no byte-level file access. |
| Parse PDFs in the Prime's MicroPython | Technically possible, but needs pure-Python inflate, a content-stream interpreter, and font rasterization (Type1/CFF/TrueType) running in an interpreter. Expect several seconds per page and unreliable output. |
| **Rasterize on the PC, decode PNG natively on the Prime** | The firmware's PNG decoder (`AFiles` → GROB) and scaled `BLIT_P` run as native code. Text quality is exactly PDFium's (Chrome's PDF engine). **Chosen.** |

The converter uses PDFium through `pypdfium2`: a single native library of about
6 MB. It writes PNGs with its own stdlib-only encoder (`primedf/png.py`) and has
no imaging library. That keeps the standalone executable small.

## File format

A document is a set of PNG files inside the PrimeDF app:

```
<doc>.<NNN>.png      doc = [A-Za-z0-9_]{1,16}, NNN = 001..999 (1-based)
```

- The app scans `AFiles()` at startup. A document's page count is its highest `NNN`.
- Images are 8-bit grayscale by default (`--rgb` gives 24-bit color).
- Each page is cropped to its own content box plus 6 pt of padding.
- All pages of a document share one scale: the median content width maps to
  `--width` px (default 640). Text size therefore doesn't change when you turn
  pages. A wide figure page simply comes out wider.

## Calculator app architecture

Everything is in one PPL app program, [`calculator/PrimeDF.hpppl`](../calculator/PrimeDF.hpppl).

- **`START()`**: builds the document list and shows it with the native `CHOOSE`
  menu. Using the firmware's own menu is the lightest option, and it supports
  touch and keys for free.
- **`Viewer()`**: the reading loop.
- **Page cache**: three GROB slots (`G1`–`G3`) with LRU eviction. While the app
  is idle it prefetches the next page, then the previous one. Turning pages
  forward or back is then just a blit. The current page is never evicted.
- **Rendering**: one scaled `BLIT_P` from the page GROB straight to `G0`. Only
  the margins the page doesn't cover get painted, so there's no full-screen
  clear and no flicker. The source origin is snapped to whole image pixels so
  the destination never starts off-screen.
- **Redraw on change only**: a `dirty` flag gates rendering.
- **Idle sleep**: with no fingers down, no key held and nothing left to
  prefetch, the loop blocks in `WAIT(-1)` instead of spinning.

### View model

```
pdZ        screen px per image px (zoom)
pdVX,pdVY  image coordinate shown at the screen's top-left
```

- *Fit width* means `pdZ = 320 / pageWidth`.
- Minimum zoom shows the whole page. Maximum is `pdZMAX` (3 screen px per image px).
- `ClampView()` keeps the page on screen, and centers it on any axis where it's
  smaller than the screen.
- Zooming with keys anchors on the screen center. Pinch anchors on the midpoint
  between the fingers, so two-finger panning works during a pinch.

### Input

| Source | Handling |
| --- | --- |
| `GETKEY` | Discrete actions: zoom, page turn, Esc, single d-pad steps. Autorepeated d-pad codes are ignored while the key is held. |
| `ISKEYDOWN` | Held d-pad. Scrolling is time-based and accelerates from 0.3 to 1.2 screen px/ms after 180 ms, so the speed doesn't depend on frame rate. |
| `MOUSE()` | Continuous finger state. 1 finger: drag, after an 8 px dead zone so taps stay taps. 2 fingers: pinch. |
| Tap detection | A press under 350 ms that stays in the dead zone. Two taps within 400 ms and 40 px reset the zoom. |
| `WAIT(-1)` | Idle wake-up only. A touch-down that wakes it seeds the tap tracker, so very quick taps aren't lost. Events that return within 30 ms are treated as stale queue entries and ignored. |

### Tunables

The constants at the top of the program (`pdZMAX`, `pdZSTEP`, `pdNUDGE`,
`pdOSDMS`, `pdTAPMS`, `pdDTAPMS`) can be edited without touching the logic.

## Known limitations

- No text search or text selection. Pages are images.
- Up to 999 pages per document. Split larger PDFs.
- Not yet verified on hardware. See the README status note.
