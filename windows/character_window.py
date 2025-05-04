from __future__ import annotations

import random
import threading
import tkinter as tk
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageTk

from .base_window import WindowBase
from .enum import Event


class CharacterWindow(WindowBase):
    """キャラクター画像の表示とまばたき・位置同期を司るウィンドウ."""

    #: 画像パス
    DEFAULT_IMAGE = Path("./assets/image/tekku_0.png")
    BLINK_IMAGES = [Path("./assets/image/tekku_1.png"), Path("./assets/image/tekku_2.png")]

    #: まばたき間隔の候補（秒）とその確率
    BLINK_INTERVALS = [1, 2, 3, 4, 5]
    BLINK_PROBS = [0.45, 0.25, 0.20, 0.08, 0.02]

    def __init__(self, root, syncronized_windows: List[WindowBase], x_pos: int, y_pos: int):
        # ウィンドウサイズ（画像リサイズ上限）
        self.pic_x = 250
        self.pic_y = 1000

        super().__init__(
            root,
            title="キャラウィンドウ",
            width=self.pic_x,
            height=self.pic_y,
            x_pos=x_pos,
            y_pos=y_pos,
            syncronized_windows=syncronized_windows,
            topmost_flag=True,
        )

        # ---------- Tkinter widget ---------- #
        self.canvas = tk.Canvas(self.window, width=self.pic_x, height=self.pic_y, highlightthickness=0)
        self.canvas.pack()
        self.window.attributes("-transparentcolor", self.window["bg"])

        # ---------- 画像ロード ---------- #
        self.character_images: List[ImageTk.PhotoImage] = []
        self._load_images()

        # 画像をキャンバスに配置
        self.image_ids: List[int] = [
            self.canvas.create_image(0, 0, image=img, anchor=tk.NW) for img in self.character_images
        ]
        self.current_image_index = 0
        self._update_image_visibility()

        # ---------- まばたきタイマー ---------- #
        self.blink_timer: threading.Timer | None = None
        self._schedule_blink()

        # memo_window を常に手前に（同期リストの先頭想定）
        if syncronized_windows:
            syncronized_windows[0].window.lift(self.window)

    # ------------------------------------------------------------------ #
    # 画像関連
    # ------------------------------------------------------------------ #
    def _load_images(self) -> None:
        """デフォルト + まばたき画像を読み込み、リサイズ後リストへ格納。"""
        self.character_images.clear()
        paths = [self.DEFAULT_IMAGE] + self.BLINK_IMAGES
        for p in paths:
            if not p.is_file():
                raise FileNotFoundError(p)
            self.character_images.append(self._prepare_image(Image.open(p)))

    def _prepare_image(self, image: Image.Image) -> ImageTk.PhotoImage:
        image = self._make_background_fully_transparent(image, (255, 0, 0), tolerance=35)
        image = self._resize_image(image, self.pic_x, self.pic_y)
        return ImageTk.PhotoImage(image)

    @staticmethod
    def _resize_image(image: Image.Image, max_w: int, max_h: int) -> Image.Image:
        ratio = min(max_w / image.width, max_h / image.height)
        return image.resize((int(image.width * ratio), int(image.height * ratio)))

    @staticmethod
    def _make_background_fully_transparent(
        image: Image.Image, color: Tuple[int, int, int], tolerance: int
    ) -> Image.Image:
        image = image.convert("RGBA")
        datas = [
            (255, 255, 255, 0) if all(abs(c - ref) <= tolerance for c, ref in zip(pixel[:3], color)) else pixel
            for pixel in image.getdata()
        ]
        image.putdata(datas)
        # 半透明ピクセルを完全透明に
        w, h = image.size
        for x in range(w):
            for y in range(h):
                *rgb, a = image.getpixel((x, y))
                if a != 255:
                    image.putpixel((x, y), (*rgb, 0))
        return image

    def _update_image_visibility(self) -> None:
        for idx, item in enumerate(self.image_ids):
            self.canvas.itemconfig(item, state="normal" if idx == self.current_image_index else "hidden")

    # ------------------------------------------------------------------ #
    # イベントオーバーライド
    # ------------------------------------------------------------------ #
    def mouse_down(self, e):
        self._lift_windows()
        return super().mouse_down(e)

    def on_focus_in(self, _event):
        self._lift_windows()

    def mouse_double_click(self, _event):
        self.notify_observers(Event.START_MENU_MODE)

    def update(self, event):
        super().update(event)
        if event == Event.SET_WINDOWPOS:
            self._check_relative_positions()

    # ------------------------------------------------------------------ #
    # 内部ユーティリティ
    # ------------------------------------------------------------------ #
    def _lift_windows(self):
        memo_win = hand_win = None
        for win in self.syncronized_windows:
            if win.title == "メモウィンドウ":
                memo_win = win
            elif win.title == "ハンドウィンドウ":
                hand_win = win
        if hand_win:
            hand_win.window.lift(self.window)
        if memo_win:
            memo_win.window.lift(self.window)

    # ---- 相対位置・透過状態の同期 ---- #
    def _check_relative_positions(self):
        base_x, base_y = self.window.winfo_x(), self.window.winfo_y()
        for idx, win in enumerate(self.syncronized_windows):
            rel_x, rel_y = self.relative_pos[idx]
            expect_x, expect_y = base_x + rel_x, base_y + rel_y
            cur_x, cur_y = win.window.winfo_x(), win.window.winfo_y()
            if win.title == "吹き出しウィンドウ":
                if abs(cur_x - expect_x) > 150 or abs(cur_y - expect_y) > 150:
                    win.setPos(expect_x, expect_y)
                    self._lift_windows()
            elif (cur_x, cur_y) != (expect_x, expect_y):
                win.setPos(expect_x, expect_y)
                self._lift_windows()

    def _check_transparency(self):
        for win in self.syncronized_windows:
            if win.translucent != self.translucent:
                win.turn_translucent()

    # ---- まばたき ---- #
    BLINK_SEQUENCE = [0, 1, 2, 1, 0]
    BLINK_TIMES = [0.08, 0.06, 0.05, 0.06, 0.08]

    def _schedule_blink(self):
        delay = random.choices(self.BLINK_INTERVALS, self.BLINK_PROBS)[0]
        self.blink_timer = threading.Timer(delay, self._start_blinking)
        self.blink_timer.start()

    def _start_blinking(self):
        self._check_relative_positions()
        self._check_transparency()
        self.blink_index = 0
        self._blink_step()

    def _blink_step(self):
        if self.blink_index >= len(self.BLINK_SEQUENCE):
            self._schedule_blink()
            return
        self.current_image_index = self.BLINK_SEQUENCE[self.blink_index]
        self._update_image_visibility()
        delay = self.BLINK_TIMES[self.blink_index]
        self.blink_index += 1
        self.blink_timer = threading.Timer(delay, self._blink_step)
        self.blink_timer.start()
