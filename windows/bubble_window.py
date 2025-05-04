from .base_window import WindowBase
import tkinter as tk
from tkinter import font as tkfont
from atproto import Client
from atproto_client.exceptions import ModelError
from PIL import Image, ImageTk
from .utils.password import generate_key, save_credentials, load_credentials
from .utils.post import extract_post_content, fetch_image
import os
import random
import threading
from .enum import Event


class BubbleWindow(WindowBase):
    # 定数定義
    DEFAULT_WINDOW_WIDTH = 300
    WINDOW_PADDING = 30
    DEFAULT_WINDOW_HEIGHT = 100
    BALLOON_COLOR = "#EFFBFB"
    FONT_COLOR = "black"
    TRANSPARENT_COLOR = "#f0f0f0"
    DEFAULT_POST_INTERVAL = 30  # seconds
    TEXT_ANIMATION_DELAY = 50  # ms
    LIKE_BUTTON_FONT = ("San Francisco", 22)
    LIKE_BUTTON_COLOR = "#ec4899"
    
    def __init__(self, root, x_pos, y_pos):
        # ウィンドウサイズ設定
        self.window_width = self.DEFAULT_WINDOW_WIDTH + self.WINDOW_PADDING
        self.window_height = self.DEFAULT_WINDOW_HEIGHT
        
        # 状態管理フラグ
        self.hovering = False
        self.stop_post_update = False
        self.is_sns_mode = True
        self.isLogined = False
        self.like_button_pressed = False
        
        # UI設定
        self.font = tkfont.Font(family="San Francisco", size=10)
        
        # 初期化
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
        self._initialize_window()
        self._setup_authentication()
        self._setup_sns_updates()

    def _initialize_window(self):
        """ウィンドウの基本設定を行う"""
        self.window.attributes("-transparentcolor", self.TRANSPARENT_COLOR)
        self._setup_canvas()
        
    def _setup_canvas(self):
        """Canvasウィジェットを設定"""
        self.canvas = tk.Canvas(
            self.window,
            width=self.window_width,
            height=self.window_height,
            bg=self.TRANSPARENT_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack()

    def _setup_authentication(self):
        """認証関連の初期設定"""
        if not os.path.exists("data/secret.key"):
            generate_key()
        self.bluesky_login()

    def _setup_sns_updates(self):
        """SNS投稿更新の初期設定"""
        if self.isLogined:
            self.set_balloons()
            self.update_sns_posts()
            self._start_sns_update_timer()

    def _start_sns_update_timer(self):
        """SNS投稿更新タイマーを開始"""
        self.update_sns_timer = threading.Timer(
            self.DEFAULT_POST_INTERVAL, 
            self.fetch_and_update_sns_posts
        )
        self.update_sns_timer.start()

    # === バルーン/UI関連メソッド ===
    def set_balloons(self):
        """吹き出しのUIを設定"""
        self._clear_canvas_elements("balloon")
        self._adjust_window_size()
        self._draw_balloon_tail()
        self._draw_rounded_rectangle()
        self.canvas.tag_lower("all")

    def _clear_canvas_elements(self, tag):
        """Canvas上の要素をクリア"""
        self.canvas.delete(tag)

    def _adjust_window_size(self):
        """ウィンドウサイズを調整"""
        self.window.geometry(f"{self.window_width}x{self.window_height}")
        self.canvas.config(height=self.window_height, width=self.window_width)

    def _draw_balloon_tail(self):
        """吹き出しのしっぽを描画"""
        hukidasi_height = min(self.window_height / 2, 40)
        triangle = [
            (self.DEFAULT_WINDOW_WIDTH, hukidasi_height - 5),
            (self.DEFAULT_WINDOW_WIDTH + 10, hukidasi_height),
            (self.DEFAULT_WINDOW_WIDTH, hukidasi_height + 5),
        ]
        self.canvas.create_polygon(
            triangle, 
            fill=self.BALLOON_COLOR, 
            outline=self.BALLOON_COLOR, 
            tags="balloon"
        )

    def _draw_rounded_rectangle(self):
        """角丸の長方形を描画"""
        radius = 10
        # 四隅の円
        positions = [
            (0, 0, radius * 2, radius * 2),  # 左上
            (self.DEFAULT_WINDOW_WIDTH - radius * 2, 0, self.DEFAULT_WINDOW_WIDTH, radius * 2),  # 右上
            (0, self.window_height - radius * 2, radius * 2, self.window_height),  # 左下
            (self.DEFAULT_WINDOW_WIDTH - radius * 2, self.window_height - radius * 2, 
             self.DEFAULT_WINDOW_WIDTH, self.window_height),  # 右下
        ]
        
        for pos in positions:
            self.canvas.create_oval(
                *pos,
                fill=self.BALLOON_COLOR,
                outline=self.BALLOON_COLOR,
                tags="balloon"
            )
        
        # 中央部分
        self.canvas.create_rectangle(
            radius,
            0,
            self.DEFAULT_WINDOW_WIDTH - radius,
            self.window_height,
            fill=self.BALLOON_COLOR,
            outline=self.BALLOON_COLOR,
            tags="balloon",
        )
        self.canvas.create_rectangle(
            0,
            radius,
            self.DEFAULT_WINDOW_WIDTH,
            self.window_height - radius,
            fill=self.BALLOON_COLOR,
            outline=self.BALLOON_COLOR,
            tags="balloon",
        )

    # === SNS認証関連メソッド ===
    def bluesky_login(self):
        """Blueskyにログイン"""
        if not os.path.exists("data/credentials.json"):
            return

        loaded_username, loaded_password = load_credentials()
        try:
            self.client.login(loaded_username, loaded_password)
            self.isLogined = True
        except Exception as e:
            print(f"Login failed: {e}")
            self.isLogined = False

    # === SNS投稿表示関連メソッド ===
    def update_sns_posts(self):
        """SNS投稿を更新"""
        if not self._should_update_sns():
            return
            
        self._reset_like_button_state()
        self._clear_post_content()
        
        response = self._safe_timeline()
        if not response.feed:
            return
            
        post = self._select_random_post(response)
        if not self._should_update_sns():  # 再度チェック
            return
            
        self._display_post_content(post)

    def _should_update_sns(self):
        """SNS更新が必要かチェック"""
        return self.is_sns_mode and not self.stop_post_update and self.isLogined

    def _reset_like_button_state(self):
        """いいねボタンの状態をリセット"""
        self.like_button_pressed = False

    def _clear_post_content(self):
        """投稿内容をクリア"""
        self.canvas.delete("all")

    def _select_random_post(self, response):
        """ランダムに投稿を選択"""
        rand_int = random.randint(0, len(response.feed) - 1)
        return response.feed[rand_int].post

    def _display_post_content(self, post):
        """投稿内容を表示"""
        post_text, image_url = extract_post_content(post)
        print(f"Image URL: {image_url}")

        self._display_text_content(post_text)
        self._display_image_content(image_url)
        self._display_like_button(post)
        self._adjust_window_height(post_text, image_url)
        self.set_balloons()

    def _display_text_content(self, post_text):
        """テキスト内容を表示"""
        if not post_text.strip():
            return
            
        self.post_label = tk.Message(
            self.canvas,
            text=post_text,
            width=self.window_width - 50,
            anchor="nw",
            justify="left",
            bg=self.BALLOON_COLOR,
            font=self.font,
            fg=self.FONT_COLOR,
        )
        self.canvas.create_window(5, 10, window=self.post_label, anchor="nw", tags="post_text")
        self.label_height = self.post_label.winfo_reqheight()
        self.current_text_index = 0
        self.full_text = post_text
        self._animate_text_display()

    def _animate_text_display(self):
        """テキストをアニメーション表示"""
        if self.current_text_index < len(self.full_text):
            self.post_label.config(text=self.full_text[:self.current_text_index + 1])
            self.current_text_index += 1
            self.canvas.after(self.TEXT_ANIMATION_DELAY, self._animate_text_display)
        else:
            self.display_image()

    def _display_image_content(self, image_url):
        """画像内容を表示"""
        self.image_height = 0
        self.image = None
        
        if image_url:
            self.image = fetch_image(
                image_url, 
                max_width=self.window_width - 50, 
                max_height=330
            )
            self.image_height = self.image.height if self.image else 0
            self.display_image()

    def display_image(self):
        """画像を表示"""
        if hasattr(self, "image") and self.image:
            self.photo_image = ImageTk.PhotoImage(self.image)
            image_label = tk.Label(
                self.canvas, 
                image=self.photo_image, 
                bg=self.BALLOON_COLOR, 
                foreground=self.FONT_COLOR
            )
            self.canvas.create_window(
                5, 
                self.label_height + 20, 
                window=image_label, 
                anchor="nw", 
                tags="post_image"
            )

    def _display_like_button(self, post):
        """いいねボタンを表示"""
        if post.viewer.like is None:
            self._create_like_button(post, "♡", "lightgray")
        else:
            self._create_like_button(post, "♥", self.LIKE_BUTTON_COLOR, pressed=True)

    def _create_like_button(self, post, text, color, pressed=False):
        """いいねボタンを作成"""
        self.like_label = tk.Label(
            self.canvas,
            text=text,
            font=self.LIKE_BUTTON_FONT,
            height=1,
            fg=color,
            bg=self.BALLOON_COLOR,
            cursor="hand2" if not pressed else "",
        )
        
        if not pressed:
            self.like_label.bind(
                "<Button-1>", 
                lambda event: self.like_post(post.uri, post.cid)
            )
            
        like_label_y = (
            self.label_height + 20 + self.image_height + 1 
            if self.image_height > 0 
            else self.label_height + 6
        )
        self.canvas.create_window(7, like_label_y, anchor="nw", window=self.like_label)

    def _adjust_window_height(self, post_text, image_url):
        """ウィンドウ高さを調整"""
        if self.image_height == 0:
            self.window_height = 10 + self.label_height + 31
        else:
            self.window_height = 10 + self.label_height + 20 + self.image_height + 26

    def like_post(self, uri, cid):
        """投稿にいいねする"""
        if not self.like_button_pressed:
            self.like_label.config(text="♥", fg=self.LIKE_BUTTON_COLOR, font=self.LIKE_BUTTON_FONT)
            self.client.like(uri=uri, cid=cid)
            self.like_button_pressed = True
            self.notify_observers(Event.SET_WINDOWPOS)

    def _safe_timeline(self, limit=50):
        """
        タイムラインを安全に取得
        1) 通常の strict=True で試す
        2) ModelError → strict 検証を完全に回避した RAW 版で再取得
        """
        try:
            return self.client.get_timeline(limit=limit)  # strict=True
        except ModelError as e:
            print(f"strict mode failed, switch to raw: {e}")
            raw = self.client.app.bsky.feed.get_timeline_raw(params={"limit": limit})
            
            class _Dummy:
                def __init__(self, d):
                    self.feed, self.cursor = d["feed"], d.get("cursor")
                    
            return _Dummy(raw)

    # === SNS更新スケジューリング関連 ===
    def update_sns_posts_async(self):
        """非同期でSNS投稿を更新"""
        if self._should_update_sns():
            self._start_sns_update_timer()

    def fetch_and_update_sns_posts(self):
        """SNS投稿を取得して更新"""
        self.update_sns_posts()
        self.update_sns_posts_async()

    def stop_update_sns_posts(self):
        """SNS投稿更新を停止"""
        self.stop_post_update = True
        if hasattr(self, 'update_sns_timer') and self.update_sns_timer:
            self.update_sns_timer.cancel()

    # === メニュー関連メソッド ===
    def menu_mode(self):
        """メニューモードに切り替え"""
        self.stop_update_sns_posts()
        self.window.lift()
        self.show_balloon()
        self._reinitialize_canvas()
        self._display_menu_options()

    def _reinitialize_canvas(self):
        """Canvasを再初期化"""
        self.canvas.destroy()
        self.canvas = tk.Canvas(
            self.window,
            width=self.window_width,
            height=self.window_height,
            bg=self.TRANSPARENT_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.delete("all")

    def _display_menu_options(self):
        """メニューオプションを表示"""
        options = ["SNS (Bluesky)の設定をする", "さようなら", "なんでもない"]
        label_height = 0

        for option in options:
            label = self._create_menu_label(option, label_height)
            label_height += label.winfo_reqheight() + 10

        self._adjust_menu_window_size(label_height)

    def _create_menu_label(self, option, y_position):
        """メニューラベルを作成"""
        label = tk.Label(
            self.canvas,
            text=option,
            font=self.font,
            bg=self.BALLOON_COLOR,
            anchor="nw",
            justify="left",
            cursor="hand2",
            foreground=self.FONT_COLOR,
        )
        
        # イベントバインディング
        bindings = {
            "<Button-1>": lambda e, opt=option: self._handle_menu_selection(opt),
            "<Enter>": lambda e, lbl=label: self._highlight_label(lbl),
            "<Leave>": lambda e, lbl=label: self._unhighlight_label(lbl),
        }
        
        for event, callback in bindings.items():
            label.bind(event, callback)
            
        label.original_font = label.cget("font")
        self.canvas.create_window(10, y_position + 10, anchor="nw", window=label)
        return label

    def _adjust_menu_window_size(self, total_height):
        """メニューウィンドウサイズを調整"""
        self.window_height = total_height + 10
        self.window.geometry(f"{self.window_width}x{self.window_height}")
        self.set_balloons()

    def _handle_menu_selection(self, option):
        """メニュー選択を処理"""
        handlers = {
            "SNS (Bluesky)の設定をする": self.handle_sns_settings,
            "さようなら": self.handle_exit,
            "なんでもない": self.handle_cancel,
        }
        handler = handlers.get(option)
        if handler:
            handler()

    def _highlight_label(self, label):
        """ラベルをハイライト"""
        label.config(bg="#d1e7e7")

    def _unhighlight_label(self, label):
        """ラベルハイライトを解除"""
        label.config(bg=self.BALLOON_COLOR)
        label.config(font=label.original_font)

    # === メニューオプション処理 ===
    def handle_sns_settings(self):
        """SNS設定メニューを表示"""
        self.canvas.delete("all")
        
        # ログインオプション
        login_label = self._create_clickable_label(
            "ログイン", 
            self.display_login_form,
            y_position=10
        )
        
        # SNS表示切り替えオプション
        display_status = "表示" if self.is_sns_mode else "非表示"
        sns_display_label = self._create_clickable_label(
            f"SNS投稿表示の切り替え (現在：{display_status})",
            self.toggle_sns_display,
            y_position=50
        )
        
        # キャンセルオプション
        cancel_label = self._create_clickable_label(
            "なんでもない",
            self.handle_cancel,
            y_position=90
        )
        
        self._adjust_menu_window_size(120)

    def _create_clickable_label(self, text, command, y_position):
        """クリック可能なラベルを作成"""
        label = tk.Label(
            self.canvas,
            text=text,
            font=self.font,
            bg=self.BALLOON_COLOR,
            fg=self.FONT_COLOR,
            cursor="hand2",
        )
        
        label.bind("<Button-1>", lambda e: command())
        label.bind("<Enter>", lambda e, lbl=label: self._highlight_label(lbl))
        label.bind("<Leave>", lambda e, lbl=label: self._unhighlight_label(lbl))
        label.original_font = label.cget("font")
        
        self.canvas.create_window(10, y_position, anchor="nw", window=label)
        return label

    def toggle_sns_display(self):
        """SNS表示を切り替え"""
        self.is_sns_mode = not self.is_sns_mode
        if self.stop_post_update:
            self.stop_update_sns_posts()
        self.display_confirmation_and_return()

    def handle_exit(self):
        """終了処理"""
        self.display_goodbye_and_exit()

    def handle_cancel(self):
        """キャンセル処理"""
        self.display_confirmation_and_return()

    # === ログイン関連メソッド ===
    def display_login_form(self):
        """ログインフォームを表示"""
        self.canvas.delete("all")
        
        # タイトル
        self._create_static_label("IDとパスワードを入力してね", 10)
        
        # ID入力
        self._create_static_label("ID:", 40)
        self.id_entry = self._create_entry(80, 40)
        
        # パスワード入力
        self._create_static_label("パスワード:", 70)
        self.pw_entry = self._create_entry(80, 70, show="*")
        
        # 保存された認証情報を読み込む
        if os.path.exists("data/credentials.json"):
            loaded_username, loaded_password = load_credentials()
            self.id_entry.insert(0, loaded_username)
            self.pw_entry.insert(0, loaded_password)
        
        # OKボタン
        ok_button = tk.Button(
            self.canvas,
            text="OK",
            font=self.font,
            command=lambda: self.attempt_login(
                self.id_entry.get(),
                self.pw_entry.get()
            ),
            bg="white",
        )
        self.canvas.create_window(10, 100, anchor="nw", window=ok_button)
        
        self._adjust_menu_window_size(150)

    def _create_static_label(self, text, y_position):
        """静的なラベルを作成"""
        label = tk.Label(
            self.canvas,
            text=text,
            font=self.font,
            bg=self.BALLOON_COLOR,
            fg=self.FONT_COLOR,
        )
        self.canvas.create_window(10, y_position, anchor="nw", window=label)
        return label

    def _create_entry(self, x, y, show=None):
        """入力フィールドを作成"""
        entry = tk.Entry(self.canvas, font=self.font, show=show)
        self.canvas.create_window(x, y, anchor="nw", window=entry)
        return entry

    def attempt_login(self, username, password):
        """ログインを試行"""
        try:
            self.client.login(username, password)
            save_credentials(username, password)
            self.display_login_result("ログインしたよ")
            self.isLogined = True
        except Exception as e:
            print(f"Login error: {e}")
            self.display_login_result("失敗したよ……")
            self.isLogined = False

    def display_login_result(self, message):
        """ログイン結果を表示"""
        self.canvas.delete("all")
        self._create_static_label(message, 10)
        
        self._adjust_menu_window_size(50)
        
        if message == "ログインしたよ":
            self.window.after(3000, self.return_to_sns_mode)
        else:
            self.window.after(3000, self.hide_balloon)

    # === ウィンドウ表示制御 ===
    def hide_balloon(self):
        """バルーンを非表示"""
        self.window.wm_attributes("-alpha", 0.0)
        self.current_alpha = 0.0

    def show_balloon(self):
        """バルーンを表示"""
        alpha = 0.5 if self.translucent else 1.0
        self.window.wm_attributes("-alpha", alpha)
        self.current_alpha = 1.0

    # === 確認メッセージ表示 ===
    def display_confirmation_and_return(self):
        """確認メッセージを表示して戻る"""
        self.canvas.delete("all")
        self._create_static_label("おっけー", 10)
        
        self._adjust_menu_window_size(40)
        
        if self.isLogined and self.is_sns_mode:
            self.window.after(4000, self.return_to_sns_mode)
        else:
            self.window.after(4000, self.hide_balloon)

    def display_goodbye_and_exit(self):
        """さよならメッセージを表示して終了"""
        self.stop_update_sns_posts()
        self.canvas.delete("all")
        self._create_static_label("じゃあね！", 10)
        
        self._adjust_menu_window_size(40)
        self.window.after(3000, self.exit_application)

    def exit_application(self):
        """アプリケーションを終了"""
        if hasattr(self, 'update_sns_timer'):
            self.update_sns_timer.join()
        self.root.destroy()

    def return_to_sns_mode(self):
        """SNSモードに戻る"""
        self.hide_balloon()
        self.stop_post_update = False
        self.fetch_and_update_sns_posts()
        self.show_balloon()

    # === イベントハンドリング ===
    def update(self, event):
        """イベントを処理"""
        super().update(event)
        if event == Event.START_MENU_MODE:
            self.menu_mode()