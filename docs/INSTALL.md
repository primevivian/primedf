# Installing PrimeDF

PrimeDF has two parts. The **converter** runs on your PC. The **PrimeDF app**
runs on the calculator.

## 1. Get the converter (PC)

Download the file for your system from the
[latest release](https://github.com/primevivian/primedf/releases/latest):

| System | File |
| --- | --- |
| Windows 10/11 (64-bit) | `PrimeDF-windows-x64.exe`: a small app with a window |
| Linux (x86-64) | `primedf-linux-x64`: command line |
| macOS (Apple silicon) | `primedf-macos-arm64`: command line |

It's a single portable file with nothing to install. Keep it anywhere, for
example on your desktop.

> [!NOTE]
> Windows SmartScreen may warn about an unsigned download. Choose
> *More info → Run anyway*. On macOS, right-click the file and choose **Open**
> the first time. On Linux and macOS, run `chmod +x` on the file first.

If you prefer Python (3.10+), you can install from source instead with
`pip install ./converter`. That gives you `primedf` (command line) and
`primedf-gui` (the window).

## 2. Convert documents

**On Windows:** open `PrimeDF-windows-x64.exe` and drop PDFs into the window,
or click it to choose files. You can also drop PDFs, or a whole folder of
them, onto the `.exe` icon. Tick **Sharper zoom** if you want crisper text
when zoomed in. When it's done, click **Open folder**.

**From a terminal:**

```sh
primedf "Linear Algebra.pdf"
# Linear Algebra.pdf: 212 pages -> Linear Algebra (9120 KiB)
```

Either way, the pages go into a folder **named after the PDF**, next to it:
`Linear Algebra\Linear_Algebra.001.png`, `Linear_Algebra.002.png`, and so on.
The file-name part before the page number is the name that shows in the
calculator menu. In a terminal, `-n` picks a shorter name and `-o` picks a
different folder:

```sh
primedf "Linear Algebra.pdf" -n LinAlg -o D:\calc
```

The Windows app runs in command-line mode with `PrimeDF-windows-x64.exe --cli ...`.
It doesn't print any output there, so use the Python package if you want to
see progress in a terminal.

## 3. Install the PrimeDF app (calculator, one time)

PrimeDF is an *app*, so its page images live inside it and its program can read
them through `AFiles`.

### Drag and drop (recommended)

1. Download `PrimeDF.hpappdir.zip` from the
   [latest release](https://github.com/primevivian/primedf/releases/latest) and
   unzip it. You get a folder called `PRIMEDF.hpappdir`.
2. Connect the calculator over USB and start **HP Connectivity Kit**.
3. Drag the `PRIMEDF.hpappdir` folder onto **Application Library** under your
   calculator in the *Calculators* pane.

That's it. The app comes with the program and its pink calculator icon.

> [!NOTE]
> If the Apps screen shows a plain icon, open PrimeDF once, then go back.
> Community reports say custom icons sometimes appear only after the app has
> been opened or saved on the calculator.

### By hand (fallback)

1. On the calculator, press <kbd>Apps</kbd>, highlight **Function**, tap
   **Save**, enter `PrimeDF`, and confirm.
2. In Connectivity Kit, expand your calculator, then
   **Application Library → PrimeDF**, and double-click **Program**.
3. Replace everything in it with the contents of
   [`calculator/PrimeDF.hpppl`](../calculator/PrimeDF.hpppl) and save
   (<kbd>Ctrl</kbd>+<kbd>S</kbd>). Connectivity Kit checks the syntax when it
   saves.

## 4. Copy page images

In Connectivity Kit's *Calculators* pane, expand your calculator, then
**Application Library → PrimeDF**. The app has two folders, **Files** and
**Variables**. Select all the `.png` files in the converter's output folder and
drag them onto **Files**.

```
HP Prime
└── Application Library
    └── PrimeDF
        ├── Files        ← page images go here (icon.png is here too)
        └── Variables    (not needed)
```

The app's files are a flat list with no subfolders. That's fine, because PrimeDF
groups pages by document name: `My_Book.001.png … My_Book.240.png` appear as
one menu entry, "My_Book (240 pages)".

To remove a document, delete its `.png` files from **Files**. Leave `icon.png`
alone.

## 5. Read

Press <kbd>Apps</kbd> and open **PrimeDF**. You can tap its icon, press **Start**,
or press <kbd>Symb</kbd>, <kbd>Plot</kbd> or <kbd>Num</kbd> inside the app: all of them open
the document menu. Press <kbd>Esc</kbd> in the menu to go back to Home.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "no documents found" | The PNGs aren't in *this* app's files, or they were renamed. Names must look like `name.001.png`. |
| "cannot open name.NNN.png" | A page in the sequence is missing. Copy the whole set again. |
| Pages are blank or the app errors on load | Convert with `--rgb` in case your firmware rejects grayscale PNGs. Please also open an issue with your firmware version. |
| Out of memory on huge pages | Convert with a smaller `-w`, and leave trimming on (don't pass `--no-trim`). Cropping keeps the images small. |
| Syntax error when saving the program | Make sure you copied the whole file, including the `#pragma` line at the top. |
| Text is tiny | Zoom in with <kbd>+</kbd> or pinch. Fit-width on a 320 px screen is an overview. |
