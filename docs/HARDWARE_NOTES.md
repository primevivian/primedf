# HP Prime G2 app programs: findings from real hardware

These notes record what PrimeDF's tests found about **app programs** on a real
HP Prime G2: an app made by saving a copy of a built-in app, whose program has
`START()` and view functions. We found little of this written down anywhere,
and the most important finding (§1) can't be found by reading the code.

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

## 1. `!=` is not "not equal" in PPL

**Confirmed (test 6, key 4).** In HP PPL, `a != b` does **not** test
inequality. It is read as `a!` (factorial) followed by `= b`:

- On **strings**, such as `IF fn!="icon.png" THEN`, it fails **at run time**.
- The program **compiles**, and the editor's **Check reports no errors**.
- **`IFERR` doesn't catch it** (test 5 and step 2c wrapped it, and still
  failed).
- When it happens inside `START()`, there's **no error message**. The app
  just opens on its base app's normal screen, which for a copy of Function is
  the Symbolic view (F1…F0, soft keys *Edit ✓ x Show Eval*). From outside it
  looks exactly like "the program never ran".

That one operator caused every failed test: the withdrawn 0.2.0 reader, steps
2/2b/2c of the rebuild, and tests 3 and 5. It's easy to write, because `!=`
means not-equal in most other languages. **Use `<>`, `≠` or `NOT(a==b)` instead**: all three are verified (test 7).
PrimeDF's menu code compares with `==` only:

```
IF fn=="icon.png" THEN
  n:=0;            // nothing to do
ELSE
  out(SIZE(out)+1):=fn;
END;
```

[`tools/check_ppl.py`](../tools/check_ppl.py) rejects `!=`.

## 2. Silent failures: how to debug app programs

- A run-time failure inside `START()` shows **no message**. You land on the
  base app's screen (§1).
- The program editor's **Check** finds **compile** errors only.
- `IFERR … THEN … END` around `START()`'s body catches *some* errors, but not
  the `!=` failure. Keep it anyway, because it turns other failures into a
  visible screen.
- **What works:** small test apps that each add **one** feature to a program
  known to boot. For several suspects at once, make each one run only when its
  own number key is pressed (test 6). The key that throws you out is the
  culprit, and the rest of the run still reports results.
- Reasoning about likely causes wasted several rounds here. Top-level `LOCAL`,
  function names, `AFiles()`, `SIZE` and `IFERR` were all suspected; all
  turned out to be fine.

## 3. App lifecycle

| Fact | Status | Evidence |
| --- | --- | --- |
| Importing a `.hpappdir` with Connectivity Kit installs the app with its program | **Confirmed** | boot test |
| A 38×38 `icon.png` in the `.hpappdir` becomes the icon in the Apps library, right after import | **Confirmed** | all test packages |
| **Tapping the app's icon runs `START()`** | **Confirmed** | boot test drew "entry: START" |
| After `START()` returns, the app shows its default view | Unknown | |
| `STARTVIEW(-1,1)` (go to Home) from inside an app | Unknown | |
| How to open an app's program on the calculator: open the app, <kbd>Shift</kbd>+<kbd>1</kbd> (Program); the app's program is the top entry; Edit, then the **Check** soft key | **Confirmed** | |

## 4. Language and API results

| Feature | Status | Test |
| --- | --- | --- |
| `#pragma mode( separator(.,;) integer(h32) )` at the top | **Confirmed OK** | all tests |
| User functions calling user functions defined above them | **Confirmed OK** | boot |
| `LOCAL` inside functions, `REPEAT … UNTIL`, `GETKEY` | **Confirmed OK** | boot |
| Key codes: Esc 4; 1 42, 2 43, 3 44, 4 37, 5 38, 6 39, 7 32, 8 33, 9 34, 0 47 | **Confirmed OK** | t6 |
| `RECT_P(G0,x1,y1,x2,y2,edge,fill)`, `TEXTOUT_P(text,G0,x,y,font,color)`, `RGB(r,g,b)` | **Confirmed OK** | boot |
| Program-wide variables declared outside functions (`pdA:=5;`, `pdB:={};`, several on one line) | **Confirmed OK** | t1 |
| Function names `Colors`, `TextW`, `Center`, `ListPng`, `DrawMenu`, `ShowPage`, `Menu` (no clash with built-ins such as `DRAWMENU`) | **Confirmed OK** | t2 |
| `IFERR … THEN … END` (multi-line) | **Confirmed OK** | t4 |
| `G1:=AFiles("icon.png")` loads an app file (PNG) into a graphic | **Confirmed OK** | t4 |
| `GROBW_P` / `GROBH_P`, and a **scaled** `BLIT_P(G0,dx1,dy1,dx2,dy2,G1,sx1,sy1,sx2,sy2)` | **Confirmed OK** | t4 (icon drawn at 2×) |
| `"text"+number` concatenation | **Confirmed OK** | t6 result lines |
| File list: `AFiles` **and** `AFiles()` both work | **Confirmed OK** | t6 keys 1, 9 |
| `SIZE(AFiles)`, `SIZE({1,2,3})`, `fl(1)` | **Confirmed OK** | t6 keys 2, 3, 0 |
| `DIMGROB_P(G9,w,h)` scratch graphic | **Confirmed OK** | t6 key 5 |
| `TEXTOUT_P` returns a value (used as the text's end x to center text) | **Confirmed OK** (value to record) | t6 key 6 |
| `DIM` and `RIGHT` on strings | **Confirmed OK** | t6 key 7 |
| List element assignment `lst(1):=…`, `lst(2):=…` | **Confirmed OK** | t6 key 8 |
| **`a != b`** | **BROKEN**: it's `a! = b` (§1) | t6 key 4 |
| `<>`, `≠`, `NOT(a==b)` as not-equal | **Confirmed OK** | t7 keys 1–4 |
| `MOUSE()`, `WAIT(-1)`, `ISKEYDOWN`, `TICKS`, `CHOOSE` | Unknown | |

## 5. Test log

| Package | Adds to the boot test | Result |
| --- | --- | --- |
| PrimeDF 0.2.0 (full reader, withdrawn) | everything (it used `<>`, but untested features may also fail) | ❌ Function screen |
| `boot` | nothing: pink screen, "IT BOOTS", Esc exits | ✅ |
| `t1-globals` | program-wide variables | ✅ |
| `t2-names` | the menu's function names | ✅ |
| `t3-files` | file listing, loops, lists, string ops, text width; uses `!=` | ❌ (the `!=`) |
| `t4-image` | `IFERR`, loading and scaling a PNG | ✅ image shown |
| step 2 / 2b / 2c (menu) | the file menu; all used `fn!="icon.png"` | ❌ Function screen, though Check reported no errors |
| `t5-diag` | each t3 suspect in its own `IFERR`, results table | ❌ (the `!=`, past `IFERR`) |
| `t6-keys` | each suspect on its own number key | ✅ boots. Every key OK **except 4 (`!=`)**, which crashes. |
| `t7-notequal` | `<>`, `≠`, `NOT(==)`, and what `!=` computes on numbers | ✅ all keys OK |
| step 2d (menu) | step 2c with `==` only | ❌ Function screen. Its `IFERR` error screen didn't show either, so either the failure escapes `IFERR` or the error screen's own text helpers fail. |
| `t8-menu-parts` | each construct step 2d uses that no passing test covered: `FOR`, `<=`/`>=`, user functions inside arguments, `LEFT`/`MIN`/`MAX`/`IP`, a list parameter, `WHILE` + `AND` chain, an apostrophe in a string, and step 2d's exact text helpers | pending |

## 6. How to run a hardware test

1. Add a small program to `calculator/tests/NAME.hpppl`, based on `boot.hpppl`
   plus **one** new feature, or one feature per number key.
2. Push. CI checks it and builds `tests/NAME/PRIMEDF.hpappdir` (artifact
   `hardware-tests`).
3. Drag that folder onto *Application Library* in Connectivity Kit, replacing
   PrimeDF, and open the app.
4. Record the result in the tables above. "Function screen" means a run-time
   failure (see §1 and §2) or a compile error.
