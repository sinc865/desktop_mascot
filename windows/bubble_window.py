from .base_window import WindowBase
import tkinter as tk
from tkinter import font as tkfont
from atproto import Client
from PIL import Image, ImageTk
from .utils.password import generate_key, save_credentials, load_credentials
from .utils.post import extract_post_content, fetch_image
import os
import random
import threading
from .enum import Event


class BubbleWindow(WindowBase):
    def __init__(self, root, x_pos, y_pos):
        self.window_width_default = 300
        self.window_width = self.window_width_default + 30  # 30 is for padding
        self.window_height_default = 100
        self.window_height = 100
        self.balloon_color = "#EFFBFB"
        self.font = tkfont.Font(family="San Francisco", size=10)
        self.font_color = "black"
        self.hovering = False
        self.stop_post_update = False
        self.is_sns_mode = True
        self.isLogined = False
        self.like_button_pressed = False
        self.post_interval = 30
        self.update_sns_timer = threading.Timer(self.post_interval, self.fetch_and_update_sns_posts)

        super().__init__(
            root,
            "吹き出しウィンドウ",
            self.window_width,
            self.window_height,
            x_pos,
            y_pos,
            syncronized_windows=[],
            topmost_flag=True,
        )
        self.client = Client()

        self.transparent_color = "#f0f0f0"
        # ウィンドウの透過色を設定
        self.window.attributes("-transparentcolor", self.transparent_color)

        # Canvasウィジェットを作成、背景を透過させる
        self.canvas = tk.Canvas(
            self.window,
            width=self.window_width,
            height=self.window_height,
            bg=self.transparent_color,
            highlightthickness=0,
        )
        self.canvas.pack()

        # 初回のみキー生成
        if not os.path.exists("data/secret.key"):
            generate_key()
        self.bluesky_login()

        if self.isLogined:
            self.set_balloons()
        # 初回のSNS投稿をすぐに表示
        self.update_sns_posts()
        self.update_sns_posts_async()

    def set_balloons(self):

        # 既存のラベルを削除
        self.canvas.delete("balloon")
        self.window.geometry(f"{self.window_width}x{self.window_height}")
        self.canvas.config(height=self.window_height, width=self.window_width)

        hukidasi_height = min(self.window_height / 2, 40)
        # 吹き出しの尾部となる三角形を描画
        triangle = [
            (self.window_width_default, hukidasi_height - 5),  # バルーンの右端から出るように調整
            (self.window_width_default + 10, hukidasi_height),  # 三角形の先端をバルーンの中心線に合わせる
            (self.window_width_default, hukidasi_height + 5),
        ]
        balloon_color = self.balloon_color
        self.canvas.create_polygon(triangle, fill=balloon_color, outline=balloon_color, tags="balloon")
        # バルーンの本体部分を描画
        radius = 10  # 角の丸みの半径

        # 角が丸い長方形を描画するために、四隅に円を描く
        self.canvas.create_oval(
            0, 0, radius * 2, radius * 2, fill=balloon_color, outline=balloon_color, tags="balloon"
        )  # 左上の角
        self.canvas.create_oval(
            self.window_width_default - radius * 2,
            0,
            self.window_width_default,
            radius * 2,
            fill=balloon_color,
            outline=balloon_color,
            tags="balloon",
        )  # 右上の角
        self.canvas.create_oval(
            0,
            self.window_height - radius * 2,
            radius * 2,
            self.window_height,
            fill=balloon_color,
            outline=balloon_color,
            tags="balloon",
        )  # 左下の角
        self.canvas.create_oval(
            self.window_width_default - radius * 2,
            self.window_height - radius * 2,
            self.window_width_default,
            self.window_height,
            fill=balloon_color,
            outline=balloon_color,
            tags="balloon",
        )  # 右下の角

        # 中央の長方形と上下の長方形を描画して、角が丸い長方形を完成させる
        self.canvas.create_rectangle(
            radius,
            0,
            self.window_width_default - radius,
            self.window_height,
            fill=balloon_color,
            outline=balloon_color,
            tags="balloon",
        )  # 中央
        self.canvas.create_rectangle(
            0,
            radius,
            self.window_width_default,
            self.window_height - radius,
            fill=balloon_color,
            outline=balloon_color,
            tags="balloon",
        )  # 上下

        self.canvas.tag_lower("all")

    def bluesky_login(self):

        if not os.path.exists("data/credentials.json"):
            return

        loaded_username, loaded_password = load_credentials()

        try:
            self.client.login(loaded_username, loaded_password)
            self.isLogined = True
        except Exception as e:
            print(e)
            self.isLogined = False

    def like_post(self, uri, cid):
        if not self.like_button_pressed:
            self.like_label.config(text="♥", fg="#ec4899", font=("San Francisco", 22))
            self.client.like(uri=uri, cid=cid)
            self.like_button_pressed = True
            self.notify_observers(Event.SET_WINDOWPOS)

    def update_sns_posts(self):
        if self.is_sns_mode is False or self.stop_post_update or self.isLogined is False:
            return
        self.like_button_pressed = False

        self.canvas.delete("all")
        # response = self.client.get_timeline()
        response = self._safe_timeline()

        rand_int = random.randint(0, len(response.feed) - 1)

        print("response_len", len(response.feed))
        post = response.feed[rand_int].post

        if self.is_sns_mode is False or self.stop_post_update:
            return

        post_text, image_url = extract_post_content(post)
        print(image_url)

        # 既存のラベルと画像を削除
        self.canvas.delete("post_text")
        self.canvas.delete("post_image")

        self.image_height = 0
        self.image = None
        if image_url:
            self.image = fetch_image(image_url, max_width=self.window_width - 50, max_height=330)
            self.image_height = self.image.height

        self.label_height = 0
        if post_text.strip():
            # ラベルを作成して追加
            self.post_label = tk.Message(
                self.canvas,
                text=post_text,
                width=self.window_width - 50,
                anchor="nw",
                justify="left",
                bg=self.balloon_color,
                font=self.font,
                fg=self.font_color,
            )
            self.canvas.update_idletasks()  # レイアウトを確定

            self.canvas.create_window(5, 10, window=self.post_label, anchor="nw", tags="post_text")

            self.label_height = self.post_label.winfo_reqheight()
            self.current_text_index = 0
            self.full_text = post_text
            self.update_text_incrementally()
        elif self.image is not None:
            self.display_image()

            # 「いいね」ボタンを追加
        if post.viewer.like is None:
            self.like_label = tk.Label(
                self.canvas,
                text="♡",
                font=("San Francisco", 22),
                height=1,
                fg="lightgray",
                bg=self.balloon_color,
                cursor="hand2",
            )
            self.like_label.bind("<Button-1>", lambda event: self.like_post(post.uri, post.cid))
        else:
            self.like_label = tk.Label(
                self.canvas,
                text="♥",
                height=1,
                font=("San Francisco", 22),
                fg="#ec4899",
                bg=self.balloon_color,
            )
            self.like_label_pressed = True

        like_label_y = (
            self.label_height + 20 + self.image_height + 1 if self.image_height > 0 else self.label_height + 6
        )
        self.canvas.create_window(7, like_label_y, anchor="nw", window=self.like_label)

        if self.image_height == 0:
            self.window_height = 10 + self.label_height + 31
        else:
            self.window_height = 10 + self.label_height + 20 + self.image_height + 26

        self.set_balloons()

    # windows/bubble_window.py から抜粋
    from atproto_client.exceptions import ModelError

    def _safe_timeline(self, limit: int = 50):
        """
        1) 通常の strict=True で試す
        2) ModelError → strict 検証を完全に回避した RAW 版で再取得
        """
        try:
            return self.client.get_timeline(limit=limit)  # strict=True
        except ModelError as e:
            print("strict mode failed, switch to raw:", e)

            # ---- RAW で取る。embed.video も dict のまま乗るだけ ----
            raw = self.client.app.bsky.feed.get_timeline_raw(  # ← ★ポイント★
                params={"limit": limit},
            )

            # 必要なのは .feed 部分だけなので整形して返す
            # raw は dict: {"feed":[{...}, ...], "cursor": "..."}
            class _Dummy:  # 簡易ラッパ
                def __init__(self, d):
                    self.feed, self.cursor = d["feed"], d.get("cursor")

            return _Dummy(raw)

    def update_text_incrementally(self):
        if self.current_text_index < len(self.full_text):
            self.post_label.config(text=self.full_text[: self.current_text_index + 1])
            self.current_text_index += 1
            self.canvas.after(50, self.update_text_incrementally)  # 50ミリ秒毎に次の文字を表示
        else:
            self.display_image()  # 文字の表示が完了したら画像を表示

    def display_image(self):
        if hasattr(self, "image") and self.image:
            self.photo_image = ImageTk.PhotoImage(self.image)
            image_label = tk.Label(
                self.canvas, image=self.photo_image, bg=self.balloon_color, foreground=self.font_color
            )
            self.canvas.create_window(5, self.label_height + 20, window=image_label, anchor="nw", tags="post_image")

    def update_sns_posts_async(self):
        if self.is_sns_mode is True and self.stop_post_update is False and self.isLogined:
            self.update_sns_timer = threading.Timer(self.post_interval, self.fetch_and_update_sns_posts)
            self.update_sns_timer.start()

    def fetch_and_update_sns_posts(self):
        self.update_sns_posts()
        self.update_sns_posts_async()

    def stop_update_sns_posts(self):
        self.stop_post_update = True
        if self.update_sns_timer:
            self.update_sns_timer.cancel()

    def menu_mode(self):
        self.stop_update_sns_posts()  # 更新を停止
        self.window.lift()
        self.show_balloon()

        # キャンバスウィジェットを再作成
        self.canvas.destroy()
        self.canvas = tk.Canvas(
            self.window,
            width=self.window_width,
            height=self.window_height,
            bg=self.transparent_color,
            highlightthickness=0,
        )
        self.canvas.pack()
        # キャンバスのすべての要素を削除
        self.canvas.delete("all")

        # メニューとして表示するオプション
        options = ["SNS (Bluesky)の設定をする", "さようなら", "なんでもない"]
        label_height = 0

        for option in options:
            label = tk.Label(
                self.canvas,
                text=option,
                font=self.font,
                bg=self.balloon_color,
                anchor="nw",
                justify="left",
                cursor="hand2",
                foreground=self.font_color,
            )
            label.bind("<Button-1>", lambda event, opt=option: self.option_selected(opt))
            label.bind("<Enter>", lambda event, label=label: self.on_label_enter(event=event, label=label))
            label.bind("<Leave>", lambda event, label=label: self.on_label_leave(event=event, label=label))
            label.original_font = label.cget("font")  # 元のフォントを保存
            self.canvas.create_window(10, label_height + 10, anchor="nw", window=label)
            label_height += label.winfo_reqheight() + 10

        self.window_height = label_height + 10
        self.window.geometry(f"{self.window_width}x{self.window_height}")
        self.set_balloons()

    def option_selected(self, option):
        print(f"選択されたオプション: {option}")
        if option == "SNS (Bluesky)の設定をする":
            self.handle_option1()
        elif option == "さようなら":
            self.handle_option2()
        elif option == "なんでもない":
            self.handle_option3()

    def display_login_form(self):
        self.canvas.delete("all")

        label = tk.Label(
            self.canvas, text="IDとパスワードを入力してね", font=self.font, bg=self.balloon_color, fg=self.font_color
        )
        self.canvas.create_window(10, 10, anchor="nw", window=label)

        id_label = tk.Label(self.canvas, text="ID:", font=self.font, bg=self.balloon_color, fg=self.font_color)
        self.canvas.create_window(10, 40, anchor="nw", window=id_label)
        id_entry = tk.Entry(self.canvas, font=self.font)
        self.canvas.create_window(80, 40, anchor="nw", window=id_entry)

        pw_label = tk.Label(self.canvas, text="パスワード:", font=self.font, bg=self.balloon_color, fg=self.font_color)
        self.canvas.create_window(10, 70, anchor="nw", window=pw_label)
        pw_entry = tk.Entry(self.canvas, font=self.font, show="*")
        self.canvas.create_window(80, 70, anchor="nw", window=pw_entry)

        if os.path.exists("data/credentials.json"):
            loaded_username, loaded_password = load_credentials()
            id_entry.insert(0, loaded_username)
            pw_entry.insert(0, loaded_password)

        ok_button = tk.Button(
            self.canvas,
            text="OK",
            font=self.font,
            command=lambda: self.attempt_login(id_entry.get(), pw_entry.get()),
            bg="white",
        )
        self.canvas.create_window(10, 100, anchor="nw", window=ok_button)

        self.window_height = 150
        self.window.geometry(f"{self.window_width}x{self.window_height}")
        self.set_balloons()

    def attempt_login(self, username, password):
        try:
            self.client.login(username, password)
            save_credentials(username, password)
            self.display_login_result("ログインしたよ")
            self.isLogined = True
        except Exception as e:
            print(e)
            self.display_login_result("失敗したよ……")
            self.isLogined = False

    def display_login_result(self, message):
        self.canvas.delete("all")
        label = tk.Label(self.canvas, text=message, font=self.font, bg=self.balloon_color, fg=self.font_color)
        self.canvas.create_window(10, 10, anchor="nw", window=label)

        self.window_height = 50
        self.window.geometry(f"{self.window_width}x{self.window_height}")
        self.set_balloons()

        if message == "ログインしたよ":
            self.window.after(3000, self.return_to_sns_mode)
        else:
            self.window.after(3000, self.hide_balloon)

    def hide_balloon(self):
        self.window.wm_attributes("-alpha", 0.0)
        self.current_alpha = 0.0

    def show_balloon(self):
        if self.translucent:
            self.window.wm_attributes("-alpha", 0.5)
        else:
            self.window.wm_attributes("-alpha", 1.0)
        self.current_alpha = 1.0

    def handle_option1_pre(self):
        # オプション1の処理
        print("オプション1が選択されました")
        self.display_login_form()

    def handle_option1(self):
        self.canvas.delete("all")
        print("オプション1が選択されました")

        login_label = tk.Label(self.canvas, text="ログイン", font=self.font, bg=self.balloon_color, fg=self.font_color)
        login_label.bind("<Button-1>", lambda event: self.display_login_form())
        login_label.bind("<Enter>", lambda event, label=login_label: self.on_label_enter(event=event, label=label))
        login_label.bind("<Leave>", lambda event, label=login_label: self.on_label_leave(event=event, label=label))
        login_label.original_font = login_label.cget("font")  # 元のフォントを保存
        self.canvas.create_window(10, 10, anchor="nw", window=login_label)

        print("stop_post_update in display", self.is_sns_mode)
        display_status = "表示" if self.is_sns_mode else "非表示"
        sns_display_label = tk.Label(
            self.canvas,
            text=f"SNS投稿表示の切り替え (現在：{display_status})",
            font=self.font,
            bg=self.balloon_color,
            fg=self.font_color,
        )
        sns_display_label.bind("<Button-1>", lambda event: self.toggle_sns_display())
        sns_display_label.bind(
            "<Enter>", lambda event, label=sns_display_label: self.on_label_enter(event=event, label=label)
        )
        sns_display_label.bind(
            "<Leave>", lambda event, label=sns_display_label: self.on_label_leave(event=event, label=label)
        )
        sns_display_label.original_font = sns_display_label.cget("font")  # 元のフォントを保存

        self.canvas.create_window(10, 50, anchor="nw", window=sns_display_label)

        no_label = tk.Label(self.canvas, text="なんでもない", font=self.font, bg=self.balloon_color, fg=self.font_color)
        no_label.bind("<Button-1>", lambda event: self.handle_option3())
        no_label.bind("<Enter>", lambda event, label=no_label: self.on_label_enter(event=event, label=label))
        no_label.bind("<Leave>", lambda event, label=no_label: self.on_label_leave(event=event, label=label))
        no_label.original_font = sns_display_label.cget("font")  # 元のフォントを保存
        self.canvas.create_window(10, 90, anchor="nw", window=no_label)

        self.window_height = 120
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.set_balloons()

    def toggle_sns_display(self):
        print("toggled")
        self.is_sns_mode = not self.is_sns_mode
        if self.stop_post_update is True:
            self.stop_update_sns_posts()
        self.display_aaa_and_return_to_sns()

    def handle_option2(self):
        print("オプション2が選択されました")
        self.display_goodbye_and_exit()

    def handle_option3(self):
        print("オプション3が選択されました")
        self.display_aaa_and_return_to_sns()

    def display_aaa_and_return_to_sns(self):
        self.canvas.delete("all")
        label = tk.Label(self.canvas, text="おっけー", font=self.font, bg=self.balloon_color, fg=self.font_color)
        self.canvas.create_window(10, 10, anchor="nw", window=label, tags="all")

        self.window_height = label.winfo_reqheight() + 20
        self.window.geometry(f"{self.window_width}x{self.window_height}")
        self.set_balloons()

        if self.isLogined is True and self.is_sns_mode is True:
            self.window.after(4000, self.return_to_sns_mode)
        else:
            self.window.after(4000, self.hide_balloon)

    def display_goodbye_and_exit(self):
        self.stop_update_sns_posts()
        self.canvas.delete("all")
        label = tk.Label(self.canvas, text="じゃあね！", font=self.font, bg=self.balloon_color, fg=self.font_color)
        self.canvas.create_window(10, 10, anchor="nw", window=label)

        self.window_height = label.winfo_reqheight() + 20
        self.window.geometry(f"{self.window_width}x{self.window_height}")
        self.set_balloons()

        self.window.after(3000, self.exit_application)

    def exit_application(self):
        self.update_sns_timer.join()
        self.root.destroy()

    def return_to_sns_mode(self):
        print(33)
        self.hide_balloon()
        self.stop_post_update = False
        self.fetch_and_update_sns_posts()

        self.show_balloon()

    def on_label_enter(self, event, label):
        label = event.widget
        label.config(bg="#d1e7e7")

    def on_label_leave(self, event, label):
        label = event.widget
        label.config(bg=self.balloon_color)
        label.config(font=label.original_font)

    def update(self, event):
        super().update(event)
        if event == Event.START_MENU_MODE:
            print("double clicked")
            self.menu_mode()
