# HP Prime G2 app programs: findings from real hardware

These notes record what PrimeDF's tests found about **app programs** on a real
HP Prime G2: an app made by saving a copy of a built-in app, whose program has
`START()` and view functions. We found little of this written down anywhere,
and some of it contradicts what you'd expect from the documentation.

Every finding comes from a test program in
[`calculator/tests/`](../calculator/tests/), installed on the calculator and
reported back. Labels:

- **Confirmed**: seen on hardware.
- **Likely**: strongly suggested by results, awaiting a direct test.
- **Unknown**: not tested yet.

Device: HP Prime G2, current firmware *(exact version to be added)*.
Install method: a `.hpappdir` built by
[`tools/hpprime_tlv.py`](../tools/hpprime_tlv.py) and dragged onto
*Application Library* in HP Connectivity Kit (see
[HPAPPDIR_FORMAT.md](HPAPPDIR_FORMAT.md)).

---

## 1. The trap: run-time errors in `START()` are silent

**Confirmed.** If `START()` hits a **run-time** error, the calculator shows no
error message. The app simply opens on its base app's normal screen, which for
a copy of Function is the Symbolic view (F1…F0 with *Edit ✓ x Show Eval*).
From the outside it looks exactly like "the program never ran".

- The program editor's **Check** only finds **compile** errors. A program can
  pass Check and still fail this way. This happened with PrimeDF step 2: Check
  reported no errors, yet the app opened on the Function screen.
- **Do this:** wrap the body of `START()` in `IFERR … THEN … END` and draw
  your own error screen in the `THEN` branch, so a failure is visible.
  **Caveat:** this didn't catch the `AFiles`/`SIZE` failure (§3). Some
  failures get past `IFERR`, or happen before `START()` runs.
- Several days of wrong guesses (top-level `LOCAL`, function names, `<>`, …)
  came from this one trap. Rule things out with single-feature test apps, not
  with reasoning.

## 2. App lifecycle

| Fact | Status | Evidence |
| --- | --- | --- |
| Importing a `.hpappdir` with Connectivity Kit installs the app with its program | **Confirmed** | boot test |
| A 38×38 `icon.png` in the `.hpappdir` becomes the icon in the Apps library, right after import | **Confirmed** | all test packages |
| **Tapping the app's icon runs `START()`** | **Confirmed** | boot test drew "entry: START" |
| After `START()` returns, the app shows its default view | Unknown | the boot test also defined `Symb()`; result not reported yet |
| `STARTVIEW(-1,1)` (go to Home) from inside an app | Unknown | |
| How to open an app's program on the calculator: open the app, <kbd>Shift</kbd>+<kbd>1</kbd> (Program); the app's program is the top entry; Edit, then the **Check** soft key | **Confirmed** | |

## 3. Language and API results

| Feature | Status | Test |
| --- | --- | --- |
| `#pragma mode( separator(.,;) integer(h32) )` at the top | **Confirmed OK** | all tests |
| User functions calling user functions defined above them | **Confirmed OK** | boot |
| `LOCAL` inside functions, `REPEAT … UNTIL`, `GETKEY` (Esc = 4) | **Confirmed OK** | boot |
| `RECT_P(G0,x1,y1,x2,y2,edge,fill)`, `TEXTOUT_P(text,G0,x,y,font,color)`, `RGB(r,g,b)` | **Confirmed OK** | boot |
| Program-wide variables declared outside functions (`pdA:=5;`, `pdB:={};`, several on one line) | **Confirmed OK** | t1 |
| Function names `Colors`, `TextW`, `Center`, `ListPng`, `DrawMenu`, `ShowPage`, `Menu` (no clash with built-ins such as `DRAWMENU`) | **Confirmed OK** | t2 |
| `IFERR … THEN … END` | **Confirmed OK** | t4 |
| `G1:=AFiles("icon.png")` loads an app file (PNG) into a graphic | **Confirmed OK** | t4 |
| `GROBW_P` / `GROBH_P` and a **scaled** `BLIT_P(G0,dx1,dy1,dx2,dy2,G1,sx1,sy1,sx2,sy2)` | **Confirmed OK** | t4 (icon drawn at 2×) |
| Listing app files with `AFiles()` (empty parentheses), plus loops, list append, string ops, `TEXTOUT_P` return value, string+number | **Something here FAILS at run time** | t3 |
| Reading the file **list** (`AFiles` or `AFiles()`, without a file name), or `SIZE`, breaks the app **even inside `IFERR`** | **Likely** | Every failing program does this, and no passing one does. t5 and step 2c failed with these wrapped in `IFERR`. t6 isolates it. |
| `"text"+number` concatenation | Likely OK | t4 drew `"icon.png: "+w+" x "+h` and booted |
| `TEXTOUT_P` returns the x where the text ends (used to center text) | Unknown | t5. Note: font 7 "IT BOOTS" at x=95 was visibly off-center, so a guessed width isn't good enough. |
| `MOUSE()`, `WAIT(-1)`, `ISKEYDOWN`, `TICKS`, `CHOOSE` | Unknown | |

## 4. Test log

| Package | Adds to the boot test | Result |
| --- | --- | --- |
| PrimeDF 0.2.0 (full reader, withdrawn) | everything | ❌ Function screen. It also called `AFiles()`. |
| `boot` | nothing: pink screen, "IT BOOTS", Esc exits | ✅ |
| `t1-globals` | program-wide variables | ✅ |
| `t2-names` | the menu's function names | ✅ |
| `t3-files` | `AFiles()`, loops, lists, string ops, text width | ❌ Function screen |
| `t4-image` | `IFERR`, loading and scaling a PNG | ✅ image shown |
| step 2 / step 2b (menu) | the file menu, using `AFiles()` | ❌ Function screen, though Check reported no errors |
| `t5-diag` | each t3 suspect in its own `IFERR`, results table | ❌ Function screen. `IFERR` didn't help. |
| step 2c (menu) | `AFiles` without parentheses, `START()` wrapped in `IFERR` | ❌ Function screen, no error screen either |
| `t6-keys` | boot screen, and each suspect runs only when its number key is pressed | pending. If it doesn't boot, merely *containing* one of the commands breaks the app. |

## 5. How to run a hardware test

1. Add a small program to `calculator/tests/NAME.hpppl`, based on `boot.hpppl`
   plus **one** new feature.
2. Push. CI checks it and builds `tests/NAME/PRIMEDF.hpappdir` (artifact
   `hardware-tests`).
3. Drag that folder onto *Application Library* in Connectivity Kit, replacing
   PrimeDF, and open the app.
4. Record the result in the table above. "Function screen" means a run-time
   (or compile) error, see §1.
