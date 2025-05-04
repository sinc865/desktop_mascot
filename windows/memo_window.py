from __future__ import annotations

import re
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import font, ttk  # noqa: F401  # imported for future use / consistency with other windows

import customtkinter as ctk

from .base_window import WindowBase
from .enum import Event  # noqa: F401  # imported for potential callbacks elsewhere

__all__ = ["MemoWindow"]


class MemoWindow(WindowBase):
    """A memo window with autosave, checkboxes, and clickable URLs."""

    # ------------------------------------------------------------------
    # class‑level configuration constants
    # ------------------------------------------------------------------
    WIDTH: int = 250
    HEIGHT: int = 230

    FG_OUTER: str = "#000000"
    FG_INNER: str = "#FFFFFF"
    TEXT_FG: str = "#000000"
    LINK_FG: str = "blue"
    CHECKED_FG: str = "gray"

    AUTOSAVE_MS: int = 5_000  # 5 s
    FILE_PATH: Path = Path("data/memo.txt")

    # pre‑compiled regexes
    _URL_RE: re.Pattern[str] = re.compile(r"https?://[^\s]+")
    _UNCHECKED_RE: re.Pattern[str] = re.compile(r"^\[ \] ", re.MULTILINE)
    _CHECKED_RE: re.Pattern[str] = re.compile(r"^\[x\] ", re.MULTILINE)

    # ------------------------------------------------------------------
    # construction / lifecycle
    # ------------------------------------------------------------------
    def __init__(self, root: tk.Tk, x_pos: int, y_pos: int) -> None:
        # keep instance attributes that *base_window* might rely on
        self.width: int = self.WIDTH
        self.height: int = self.HEIGHT
        self.x_pos: int = x_pos
        self.y_pos: int = y_pos
        self.topmost_flag: bool = True
        self.file_path: Path = self.FILE_PATH
        self.auto_save_interval: int = self.AUTOSAVE_MS

        super().__init__(
            root,
            "メモウィンドウ",
            self.width,
            self.height,
            x_pos,
            y_pos,
            syncronized_windows=[],
            topmost_flag=True,
        )

    # ------------------------------------------------------------------
    # window setup & teardown
    # ------------------------------------------------------------------
    def setup_window(self) -> None:  # noqa: D401
        """Construct widgets, load text, and start autosave."""
        self._build_widgets()
        self._load_text()
        self._decorate_text()

        super().setup_window()

        # periodic tasks & callbacks
        self._schedule_autosave()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def on_focus_in(self, event: tk.Event) -> None:  # noqa: D401
        if self.syncronized_windows:
            self.syncronized_windows[0].window.lift(self.window)

    # ------------------------------------------------------------------
    # widget construction
    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        self.outer_frame = ctk.CTkFrame(self.window, fg_color=self.FG_OUTER, corner_radius=0)
        self.outer_frame.pack(expand=True, fill=ctk.BOTH)

        self.inner_frame = ctk.CTkFrame(self.outer_frame, fg_color=self.FG_INNER, corner_radius=0)
        self.inner_frame.pack(expand=True, fill=ctk.BOTH, padx=1, pady=1)

        self.text_widget = tk.Text(
            self.inner_frame,
            wrap=tk.WORD,
            bd=0,
            bg=self.FG_INNER,
            fg=self.TEXT_FG,
        )
        self.text_widget.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10, pady=10)

        # tag styles
        self.text_widget.tag_configure("link", foreground=self.LINK_FG, underline=True)
        self.text_widget.tag_configure("checked", foreground=self.CHECKED_FG, overstrike=True)

        # event bindings
        self.text_widget.bind("<KeyRelease>", self._decorate_text)
        self.text_widget.bind("<Button-1>", self._on_click)
        self.text_widget.tag_bind("link", "<Double-1>", self._open_link)

    # ------------------------------------------------------------------
    # text decoration helpers
    # ------------------------------------------------------------------
    def _decorate_text(self, _event: tk.Event | None = None) -> None:
        """Apply checkbox & link styling over the entire buffer."""
        content = self.text_widget.get("1.0", tk.END)

        # clear previous tags
        self.text_widget.tag_remove("link", "1.0", tk.END)
        self.text_widget.tag_remove("checked", "1.0", tk.END)

        self._apply_checkboxes(content)
        self._apply_links(content)

    def _apply_checkboxes(self, content: str) -> None:
        """Replace markdown [ ] / [x] with unicode boxes & add strike."""
        for m in self._UNCHECKED_RE.finditer(content):
            self._replace_span(m.start(), 3, "☐ ")

        for m in self._CHECKED_RE.finditer(content):
            self._replace_span(m.start(), 3, "☑ ")

        # add strike for checked lines
        pos = "1.0"
        while True:
            pos = self.text_widget.search("☑", pos, stopindex=tk.END)
            if not pos:
                break
            line_end = self.text_widget.index(f"{pos} lineend")
            self.text_widget.tag_add("checked", f"{pos} + 2c", line_end)
            pos = line_end

    def _apply_links(self, content: str) -> None:
        for m in self._URL_RE.finditer(content):
            self.text_widget.tag_add("link", f"1.0+{m.start()}c", f"1.0+{m.end()}c")

    # ------------------------------------------------------------------
    # click / URL handling
    # ------------------------------------------------------------------
    def _on_click(self, event: tk.Event) -> None:
        idx = self.text_widget.index(f"@{event.x},{event.y}")
        line_start = f"{idx.split('.')[0]}.0"
        line_text = self.text_widget.get(line_start, f"{line_start} lineend")

        if line_text.startswith("☐ "):
            self._toggle_checkbox(line_start, "☐ ", "☑ ")
        elif line_text.startswith("☑ "):
            self._toggle_checkbox(line_start, "☑ ", "☐ ")

        self._decorate_text()

    def _toggle_checkbox(self, line_start: str, old: str, new: str) -> None:
        self.text_widget.delete(line_start, f"{line_start}+{len(old)}c")
        self.text_widget.insert(line_start, new)

    def _open_link(self, event: tk.Event) -> None:
        idx = self.text_widget.index(f"@{event.x},{event.y}")
        start = self.text_widget.search("https://", idx, backwards=True, stopindex="1.0", regexp=True)
        if start:
            end = self.text_widget.search(r"\s", start, stopindex=tk.END, regexp=True) or tk.END
            url = self.text_widget.get(start, end)
            webbrowser.open(url)

    # ------------------------------------------------------------------
    # autosave & file I/O
    # ------------------------------------------------------------------
    def _schedule_autosave(self) -> None:
        self._save_text()
        self.window.after(self.auto_save_interval, self._schedule_autosave)

    def _save_text(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(self.text_widget.get("1.0", tk.END), encoding="utf-8")

    def _load_text(self) -> None:
        if self.file_path.exists():
            self.text_widget.insert("1.0", self.file_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # utility
    # ------------------------------------------------------------------
    def _replace_span(self, start_offset: int, length: int, replacement: str) -> None:
        self.text_widget.delete(f"1.0+{start_offset}c", f"1.0+{start_offset + length}c")
        self.text_widget.insert(f"1.0+{start_offset}c", replacement)

    # ------------------------------------------------------------------
    # graceful shutdown
    # ------------------------------------------------------------------
    def _on_close(self) -> None:
        self._save_text()
        self.window.destroy()

    # ------------------------------------------------------------------
    # optional overrides (kept for consistency)
    # ------------------------------------------------------------------
    def mouse_move(self, event):  # noqa: D401
        pass

    def update(self, event):  # noqa: D401
        super().update(event)
