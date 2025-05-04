from __future__ import annotations

from abc import ABC
import tkinter as tk
from typing import List, Tuple

from .enum import Event

__all__ = ["WindowBase"]


class WindowBase(ABC):
    """Foundation for the memo, character, bubble, and hand overlay windows."""

    # ---------------------------------------------------------------------
    # Construction helpers
    # ---------------------------------------------------------------------

    def __init__(
        self,
        root: tk.Tk,
        title: str,
        width: int,
        height: int,
        x_pos: int = 0,
        y_pos: int = 0,
        syncronized_windows: List["WindowBase"] | None = None,
        topmost_flag: bool = False,
    ) -> None:
        # Main tkinter handles
        self.root: tk.Tk = root
        self.window: tk.Toplevel = tk.Toplevel(root)
        self.window.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        self.title: str = title
        self.window.title(title)
        self.window.wm_attributes("-topmost", topmost_flag)
        self.window.overrideredirect(True)

        # Rendering state
        self.current_alpha: float = 1.0
        self.translucent: bool = False

        # Observer pattern
        self.observers: list[WindowBase] = []

        # Follower‑window support
        self.syncronized_windows: list[WindowBase] = []
        self.relative_pos: list[Tuple[int, int]] = []

        # Dragging helpers
        self.origin: Tuple[int, int] = (0, 0)
        self.originText: Tuple[int, int] = (0, 0)
        self.isMouseDown: bool = False
        self.isMouseDownText: bool = False

        # Register any initial follower windows and bind common events
        self.add_syncronized_window(syncronized_windows or [])
        self.setup_window()

    # ------------------------------------------------------------------
    # Observer pattern helpers
    # ------------------------------------------------------------------

    def add_observer(self, observers: List["WindowBase"]) -> None:
        """Register *observers* for event notifications."""
        self.observers.extend(observers)

    def notify_observers(self, event: Event) -> None:
        """Broadcast *event* to all observers."""
        for observer in self.observers:
            observer.update(event)

    def update(self, event: Event) -> None:  # noqa: D401
        """Default handler for incoming *event* messages."""
        if event == Event.TRUNSLUCENT:
            self.turn_translucent()

    # ------------------------------------------------------------------
    # Follower‑window management
    # ------------------------------------------------------------------

    def add_syncronized_window(self, window_list: List["WindowBase"]) -> None:
        """Attach *window_list* so they move in concert with this window."""
        main_geom = self.window.geometry().split("+")
        main_x, main_y = int(main_geom[1]), int(main_geom[2])

        for window in window_list:
            self.syncronized_windows.append(window)
            sub_geom = window.window.geometry().split("+")
            sub_x, sub_y = int(sub_geom[1]), int(sub_geom[2])
            self.relative_pos.append((sub_x - main_x, sub_y - main_y))

    # ------------------------------------------------------------------
    # Window‑level event wiring
    # ------------------------------------------------------------------

    def setup_window(self) -> None:
        """Bind generic mouse/keyboard focus callbacks."""
        self.window.bind("<Button-1>", self.mouse_down)
        self.window.bind("<Double-1>", self.mouse_double_click)
        self.window.bind("<Button-3>", self.mouse_right_down)
        self.window.bind("<ButtonRelease-1>", self.mouse_release)
        self.window.bind("<B1-Motion>", self.mouse_move)
        self.window.bind("<FocusIn>", self.on_focus_in)
        self.window.bind("<FocusOut>", self.on_focus_out)
        self.window.bind("<Enter>", self.on_mouse_enter)
        self.window.bind("<Leave>", self.on_mouse_leave)

    # ------------------------------------------------------------------
    # Event callback stubs (sub‑classes may override as needed)
    # ------------------------------------------------------------------

    def mouse_double_click(self, event: tk.Event) -> None:  # noqa: U100
        pass

    def mouse_right_down(self, event: tk.Event) -> None:  # noqa: U100
        self.notify_observers(Event.TRUNSLUCENT)
        self.turn_translucent()

    def turn_translucent(self) -> None:
        """Toggle between opaque (1.0) and translucent (0.5) alpha."""
        if self.current_alpha == 0:
            return
        self.translucent = not self.translucent
        self.current_alpha = 0.5 if self.translucent else 1.0
        self.window.attributes("-alpha", self.current_alpha)

    # ----- Optional overrides for sub‑classes --------------------------------

    def on_mouse_enter(self, event: tk.Event) -> None:  # noqa: U100
        pass

    def on_mouse_leave(self, event: tk.Event) -> None:  # noqa: U100
        pass

    def on_focus_in(self, event: tk.Event) -> None:  # noqa: U100
        pass

    def on_focus_out(self, event: tk.Event) -> None:  # noqa: U100
        pass

    def on_click(self, event: tk.Event) -> None:  # noqa: U100
        pass

    # ------------------------------------------------------------------
    # Dragging logic
    # ------------------------------------------------------------------

    def mouse_down(self, e: tk.Event) -> None:
        if e.num == 1:
            self.origin = (e.x, e.y)
            self.isMouseDown = True

    def mouse_release(self, e: tk.Event) -> None:  # noqa: N802
        self.isMouseDown = False

    def mouse_move(self, e: tk.Event) -> None:  # noqa: N802
        if self.isMouseDown:
            geom = self.window.geometry().split("+")
            new_x = e.x - self.origin[0] + int(geom[1])
            new_y = e.y - self.origin[1] + int(geom[2])

            self.setPos(new_x, new_y)
            self.syncSubWindow(e.x - self.origin[0], e.y - self.origin[1])

    # ------------------------------------------------------------------
    # Follower window movement helpers
    # ------------------------------------------------------------------

    def syncSubWindow(self, dx: int, dy: int) -> None:  # noqa: N802
        for sub_window in self.syncronized_windows:
            geom = sub_window.window.geometry().split("+")
            new_x = int(geom[1]) + dx
            new_y = int(geom[2]) + dy
            sub_window.setPos(new_x, new_y)

    # ------------------------------------------------------------------
    # Text dragging helpers (used by memo window)
    # ------------------------------------------------------------------

    def mouseDownText(self, e: tk.Event) -> None:  # noqa: N802
        if e.num == 1:
            self.originText = (e.x, e.y)
            self.isMouseDownText = True

    def mouseReleaseText(self, e: tk.Event) -> None:  # noqa: N802
        self.isMouseDownText = False

    # ------------------------------------------------------------------
    # Misc utilities
    # ------------------------------------------------------------------

    def setPos(self, x: int, y: int) -> None:  # noqa: N802
        """Move the window to absolute screen coordinates (*x*, *y*)."""
        self.window.geometry(f"+{x}+{y}")
