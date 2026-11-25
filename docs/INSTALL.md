# Installing PrimeDF

PrimeDF has two parts. The **converter** runs on your PC. The **PrimeDF app**
runs on the calculator.

## 1. Install the converter (PC)

You need Python 3.10 or newer.

```sh
git clone https://github.com/primevivian/primedf.git
cd primedf
pip install ./converter
primedf --version
```

## 2. Convert documents

```sh
primedf "Linear Algebra.pdf" -o out/
# Linear Algebra.pdf: 212 pages -> out/Linear_Algebra.*.png (9120 KiB)
```

This creates one image per page: `Linear_Algebra.001.png`,
`Linear_Algebra.002.png`, and so on. The part before the page number is the
name that shows in the calculator menu. Use `-n` to pick a shorter one:

```sh
primedf "Linear Algebra.pdf" -n LinAlg -o out/
```

## 3. Create the PrimeDF app (calculator, one time)

PrimeDF is an *app*, so its page images live inside it and its program can read
them through `AFiles`.

1. Press <kbd>Apps</kbd>.
2. Highlight **Function** (any built-in app works as the base).
3. Tap **Save**, enter `PrimeDF`, and confirm.

## 4. Install the app program

1. Connect the calculator over USB and start **HP Connectivity Kit**.
2. In the *Calculators* pane, expand your calculator, then
   **Application Library → PrimeDF**.
3. Double-click **Program** to open the editor.
4. Delete everything in it, paste the contents of
   [`calculator/PrimeDF.hpppl`](../calculator/PrimeDF.hpppl), and save
   (<kbd>Ctrl</kbd>+<kbd>S</kbd>). Connectivity Kit checks the syntax when it
   saves.

You can also type it in on the calculator. Press <kbd>Shift</kbd>+<kbd>1</kbd>
(Program catalog), open **PrimeDF (App)**, and paste the code. Connectivity Kit
is much easier.

## 5. Copy page images

Drag the `.png` files from your output folder onto the **PrimeDF** entry under
*Application Library* in Connectivity Kit. They're stored as the app's files.

To remove a document, delete its `.png` files from the app's files in
Connectivity Kit.

## 6. Read

Press <kbd>Apps</kbd> and open **PrimeDF**. If you land on the Function
screens instead of the file menu, highlight PrimeDF and tap **Start**. That
runs the app's `START()` entry point.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "no documents found" | The PNGs aren't in *this* app's files, or they were renamed. Names must look like `name.001.png`. |
| "cannot open name.NNN.png" | A page in the sequence is missing. Copy the whole set again. |
| Pages are blank or the app errors on load | Convert with `--rgb` in case your firmware rejects grayscale PNGs. Please also open an issue with your firmware version. |
| Out of memory on huge pages | Convert with a smaller `-w`, and leave trimming on (don't pass `--no-trim`). Cropping keeps the images small. |
| Syntax error when saving the program | Make sure you copied the whole file, including the `#pragma` line at the top. |
| Text is tiny | Zoom in with <kbd>+</kbd> or pinch. Fit-width on a 320 px screen is an overview. |
