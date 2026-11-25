"""PrimeDF converter window: a small, friendly front end for convert_pdf.

Built on tkinter (part of Python) so it adds almost nothing to the
executable. On Windows, PDFs can be dropped onto the window (native
WM_DROPFILES, no extra libraries) or onto the .exe icon. Everywhere else,
click the drop zone to pick files.
"""

from __future__ import annotations

import base64
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable, Sequence
from pathlib import Path
from tkinter import filedialog
from tkinter import font as tkfont

from . import __version__
from .convert import (
    DEFAULT_WIDTH,
    SHARP_WIDTH,
    ConversionError,
    convert_pdf,
    default_output_dir,
    find_pdfs,
)
from .icon import icon_png

BG = "#FFF7F2"
CARD = "#FFFFFF"
CARD_HOVER = "#FFF0F5"
ACCENT = "#FF7EA6"
ACCENT_DARK = "#E8608C"
ACCENT_SOFT = "#F7C4D4"
INK = "#3E3248"
MUTED = "#8E8299"
TRACK = "#F7E1E9"
GOOD = "#2E9E76"
BAD = "#D9435E"


# ---------------------------------------------------------------- helpers
def _rrect_points(x0: float, y0: float, x1: float, y1: float, r: float) -> list[float]:
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    return [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
            x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]


def _rrect(c: tk.Canvas, x0: float, y0: float, x1: float, y1: float, r: float,
           **kw) -> int:
    return c.create_polygon(_rrect_points(x0, y0, x1, y1, r), smooth=True, **kw)


def _enable_dpi_awareness() -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


def _open_folder(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


def enable_file_drop(widget: tk.Widget, callback: Callable[[list[str]], None]) -> bool:
    """Accept files dragged from Explorer onto ``widget`` (Windows only).

    Subclasses the widget's window procedure to handle WM_DROPFILES.
    Returns False (and changes nothing) where unsupported.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
        lresult = ctypes.c_ssize_t
        wndproc_t = ctypes.WINFUNCTYPE(lresult, wintypes.HWND, wintypes.UINT,
                                       wintypes.WPARAM, wintypes.LPARAM)
        user32.CallWindowProcW.restype = lresult
        user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                           wintypes.WPARAM, wintypes.LPARAM]
        user32.DefWindowProcW.restype = lresult
        user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                          wintypes.WPARAM, wintypes.LPARAM]
        set_long = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
        set_long.restype = ctypes.c_void_p
        set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        shell32.DragQueryFileW.restype = wintypes.UINT
        shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT,
                                           ctypes.c_wchar_p, wintypes.UINT]
        shell32.DragFinish.argtypes = [ctypes.c_void_p]
        shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]

        wm_dropfiles = 0x0233
        old_proc: list[int | None] = [None]

        def proc(hwnd, msg, wparam, lparam):
            if msg == wm_dropfiles:
                files = []
                for i in range(shell32.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)):
                    length = shell32.DragQueryFileW(wparam, i, None, 0)
                    buf = ctypes.create_unicode_buffer(length + 1)
                    shell32.DragQueryFileW(wparam, i, buf, length + 1)
                    files.append(buf.value)
                shell32.DragFinish(wparam)
                widget.after_idle(callback, files)
                return 0
            if old_proc[0] is None:
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
            return user32.CallWindowProcW(old_proc[0], hwnd, msg, wparam, lparam)

        hwnd = widget.winfo_id()
        new_proc = wndproc_t(proc)
        widget._primedf_drop_proc = new_proc  # keep the callback alive
        old_proc[0] = set_long(hwnd, -4, ctypes.cast(new_proc, ctypes.c_void_p))  # GWLP_WNDPROC
        shell32.DragAcceptFiles(hwnd, True)
        return True
    except Exception:
        return False


# -------------------------------------------------------------------- app
class ConverterApp:
    def __init__(self, root: tk.Tk, files: Sequence[str | Path] = (),
                 selftest: bool = False) -> None:
        self.root = root
        self.selftest = selftest
        self.exit_code = 0
        self.q: queue.Queue = queue.Queue()
        self.busy = False
        self.last_out: Path | None = None
        self.k = max(1.0, root.winfo_fpixels("1i") / 96.0)
        self._build()
        self.can_drop = enable_file_drop(self.zone, self.start)
        if not self.can_drop:
            self.zone.itemconfigure(self.zone_title, text="Choose PDFs")
            self.zone.itemconfigure(self.zone_sub, text="click here to pick files")
        root.report_callback_exception = self._on_tk_error
        root.after(40, self._poll)
        if files:
            root.after(250, lambda: self.start(list(files)))

    def S(self, v: float) -> int:  # noqa: N802 - tiny scaling helper
        return int(round(v * self.k))

    # ------------------------------------------------------------ layout
    def _build(self) -> None:
        root, S = self.root, self.S
        fam = tkfont.nametofont("TkDefaultFont").actual("family")
        f_title, f_sub = (fam, 18, "bold"), (fam, 10)
        f_big, f_body, f_small = (fam, 13, "bold"), (fam, 10), (fam, 9)

        root.title("PrimeDF")
        root.configure(bg=BG)
        root.resizable(False, False)
        try:
            self._icons = [tk.PhotoImage(data=base64.b64encode(icon_png(s))) for s in (64, 32, 16)]
            root.iconphoto(True, *self._icons)
        except tk.TclError:
            self._icons = []

        self.W = W = S(400)
        pad = S(22)

        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=pad, pady=(S(18), S(4)))
        if self._icons:
            tk.Label(header, image=self._icons[0], bg=BG).pack(side="left")
        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left", padx=S(10))
        tk.Label(titles, text="PrimeDF", font=f_title, fg=INK, bg=BG).pack(anchor="w")
        tk.Label(titles, text="PDF → HP Prime page converter", font=f_sub,
                 fg=MUTED, bg=BG).pack(anchor="w")

        # drop zone
        zh = self.zone_h = S(140)
        self.zone = tk.Canvas(root, width=W, height=zh, bg=BG, highlightthickness=0,
                              cursor="hand2")
        self.zone.pack(padx=pad, pady=(S(10), S(10)))
        m = S(3)
        self.zone_box = _rrect(self.zone, m, m, W - m, zh - m, S(20), fill=CARD,
                               outline=ACCENT, width=S(2), dash=(6, 4))
        self.zone_title = self.zone.create_text(W / 2, zh / 2 - S(12), text="Drop PDFs here",
                                                font=f_big, fill=INK)
        self.zone_sub = self.zone.create_text(W / 2, zh / 2 + S(14),
                                              text="or click to choose files",
                                              font=f_body, fill=MUTED)
        self.zone.bind("<Enter>", lambda e: self._hover(True))
        self.zone.bind("<Leave>", lambda e: self._hover(False))
        self.zone.bind("<Button-1>", lambda e: self.choose())

        # progress pill
        bh = self.bar_h = S(12)
        self.bar = tk.Canvas(root, width=W, height=bh, bg=BG, highlightthickness=0)
        self.bar.pack(padx=pad)
        _rrect(self.bar, 0, 0, W, bh, bh / 2, fill=TRACK, outline="")
        self.bar_fill = _rrect(self.bar, 0, 0, bh, bh, bh / 2, fill=ACCENT, outline="",
                               state="hidden")

        self.status = tk.Label(root, text="Ready when you are!", font=f_body, fg=INK, bg=BG,
                               wraplength=W, justify="left", anchor="w")
        self.status.pack(fill="x", padx=pad, pady=(S(8), S(2)))

        row = tk.Frame(root, bg=BG)
        row.pack(fill="x", padx=pad, pady=(S(8), S(2)))
        self.sharp = tk.BooleanVar(value=False)
        tk.Checkbutton(row, text="Sharper zoom (bigger files)", variable=self.sharp,
                       font=f_body, fg=INK, bg=BG, activebackground=BG, activeforeground=INK,
                       selectcolor=CARD, bd=0, highlightthickness=0,
                       cursor="hand2").pack(side="left")
        self.open_btn = tk.Button(row, text="Open folder", font=(fam, 10, "bold"),
                                  fg="white", bg=ACCENT_SOFT, activebackground=ACCENT_DARK,
                                  activeforeground="white", disabledforeground="white",
                                  relief="flat", bd=0, padx=S(14), pady=S(5),
                                  state="disabled", command=self.open_output)
        self.open_btn.pack(side="right")

        tk.Label(root, text="Next step: drag the .png files onto the PrimeDF app in "
                 "HP Connectivity Kit.", font=f_small, fg=MUTED, bg=BG, wraplength=W,
                 justify="left", anchor="w").pack(fill="x", padx=pad, pady=(S(10), S(4)))
        tk.Label(root, text=f"v{__version__}", font=f_small, fg=ACCENT_SOFT,
                 bg=BG).pack(anchor="e", padx=pad, pady=(0, S(10)))

        root.update_idletasks()
        x = (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2
        y = (root.winfo_screenheight() - root.winfo_reqheight()) // 3
        root.geometry(f"+{max(0, x)}+{max(0, y)}")
        root.lift()
        root.attributes("-topmost", True)
        root.after(400, lambda: root.attributes("-topmost", False))

    # ----------------------------------------------------------- widgets
    def _hover(self, on: bool) -> None:
        if not self.busy:
            self.zone.itemconfigure(self.zone_box, fill=CARD_HOVER if on else CARD,
                                    outline=ACCENT_DARK if on else ACCENT)

    def _set_status(self, text: str, color: str = INK) -> None:
        self.status.configure(text=text, fg=color)

    def _set_progress(self, frac: float) -> None:
        if frac <= 0:
            self.bar.itemconfigure(self.bar_fill, state="hidden")
            return
        h = self.bar_h
        x1 = max(float(h), self.W * min(1.0, frac))
        self.bar.coords(self.bar_fill, *_rrect_points(0, 0, x1, h, h / 2))
        self.bar.itemconfigure(self.bar_fill, state="normal")

    def _set_open_enabled(self, on: bool) -> None:
        self.open_btn.configure(state="normal" if on else "disabled",
                                bg=ACCENT if on else ACCENT_SOFT,
                                cursor="hand2" if on else "")

    def _on_tk_error(self, exc, val, tb) -> None:
        self._set_status(f"Oops, something went wrong: {val}", BAD)

    # ------------------------------------------------------------ actions
    def choose(self) -> None:
        if self.busy:
            return
        names = filedialog.askopenfilenames(
            parent=self.root, title="Choose PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if names:
            self.start(list(names))

    def open_output(self) -> None:
        if self.last_out is not None:
            _open_folder(self.last_out)

    def start(self, paths: Sequence[str | Path]) -> None:
        if self.busy:
            self._set_status("Still busy with the last batch, one moment!", MUTED)
            return
        pdfs = find_pdfs(paths)
        if not pdfs:
            self._set_status("Hmm, that doesn't look like a PDF. Try another file?", BAD)
            if self.selftest:
                self.exit_code = 1
                self.root.after(200, self.root.destroy)
            return
        self.busy = True
        self._set_open_enabled(False)
        self._set_progress(0)
        self.zone.itemconfigure(self.zone_box, fill=CARD, outline=ACCENT_SOFT)
        self.zone.itemconfigure(self.zone_title, text="Working on it…")
        self.zone.itemconfigure(self.zone_sub, text=f"{len(pdfs)} PDF" + ("s" * (len(pdfs) > 1)))
        width = SHARP_WIDTH if self.sharp.get() else DEFAULT_WIDTH
        threading.Thread(target=self._work, args=(pdfs, width), daemon=True).start()

    def _work(self, pdfs: list[Path], width: int) -> None:
        ok, pages, errors, last_out = 0, 0, [], None
        for i, pdf in enumerate(pdfs):
            def progress(done: int, total: int, _i: int = i, _pdf: Path = pdf) -> None:
                self.q.put(("progress", (_i + done / total) / len(pdfs),
                            f"Converting “{_pdf.name}” … page {done} of {total}"))

            self.q.put(("progress", i / len(pdfs), f"Opening “{pdf.name}” …"))
            try:
                result = convert_pdf(pdf, default_output_dir(pdf), width=width,
                                     progress=progress)
            except ConversionError as exc:
                errors.append(str(exc))
                continue
            except Exception as exc:  # keep the window alive no matter what
                errors.append(f"{pdf.name}: {exc}")
                continue
            ok += 1
            pages += result.pages
            last_out = result.out_dir
        self.q.put(("finished", ok, pages, errors, last_out))

    def _poll(self) -> None:
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "progress":
                    self._set_progress(msg[1])
                    self._set_status(msg[2])
                elif msg[0] == "finished":
                    self._finish(*msg[1:])
        except queue.Empty:
            pass
        self.root.after(40, self._poll)

    def _finish(self, ok: int, pages: int, errors: list[str], last_out: Path | None) -> None:
        self.busy = False
        self.last_out = last_out
        self._set_progress(1.0 if ok else 0)
        self.zone.itemconfigure(self.zone_box, fill=CARD, outline=ACCENT)
        if ok:
            self.zone.itemconfigure(self.zone_title, text="All done! ♥")
            self.zone.itemconfigure(self.zone_sub, text="drop more PDFs anytime" if self.can_drop
                                    else "click to convert more")
            where = (f"the “{last_out.name}” folder" if ok == 1 and last_out
                     else f"{ok} folders next to your PDFs")
            text = f"{pages} page{'s' * (pages != 1)} saved to {where}."
            if errors:
                text += "\nCouldn't convert: " + "; ".join(errors)
            self._set_status(text, BAD if errors else GOOD)
            self._set_open_enabled(last_out is not None)
        else:
            self.zone.itemconfigure(self.zone_title, text="Drop PDFs here" if self.can_drop
                                    else "Choose PDFs")
            self.zone.itemconfigure(self.zone_sub, text="or click to choose files")
            self._set_status("Couldn't convert: " + "; ".join(errors), BAD)
        if self.selftest:
            self.exit_code = 0 if ok and not errors else 1
            self.root.after(200, self.root.destroy)


def run_gui(files: Sequence[str | Path] = (), selftest: bool = False) -> int:
    _enable_dpi_awareness()
    root = tk.Tk()
    app = ConverterApp(root, files, selftest=selftest)
    if selftest:
        root.after(120_000, root.destroy)  # safety net for CI
    root.mainloop()
    return app.exit_code


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the windowed app.

    ``PrimeDF.exe [files...]``      open the window (and convert ``files``)
    ``PrimeDF.exe --cli ARGS...``   run the command-line converter instead
    ``PrimeDF.exe --gui-selftest F``  convert F through the window, then exit
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--cli"]:
        from .cli import main as cli_main

        return cli_main(args[1:])
    if args[:1] == ["--gui-selftest"]:
        return run_gui(args[1:], selftest=True)
    return run_gui(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
