# テックちゃん デスクトップマスコット

📄 [English version](./README_en.md)

<img src="https://github.com/user-attachments/assets/a19a4042-7e38-429e-b5bd-1141f385be3c" width="400" alt="デモGIF">

## 主な機能

- **メモ機能**：すぐに書き留めたいアイデアやタスクを簡単に記録できます。
- **SNS（Bluesky）投稿表示**：デスクトップ上のキャラクターが定期的にSNS投稿を取得し、表示します。表示のオン／オフは切り替え可能です。
- **透過表示**：アプリの透過度を調整でき、作業の邪魔をしない自然な表示が可能です。

## 動作環境

- 対応OS：Windows 10
- Pythonバージョン：3.13

## インストール手順

1. リポジトリをクローン：
    ```bash
    git clone https://github.com/ripiripi/desktop_mascot.git
    cd desktop_mascot
    ```

2. [uv](https://docs.astral.sh/uv/getting-started/installation/#__tabbed_1_1) で環境を構築：
    ```bash
    uv venv              
    uv sync              
    ```

3. アプリケーション実行：
    ```bash
    uv run python main.py
    ```

## 使い方

- **メモ機能**：アプリ起動時にキャラクターと共にメモウィンドウが表示され、すぐに利用可能です。メモは編集・削除ができ、内容は自動的にテキストファイルへ保存されます。

- **SNS投稿表示**：マスコットが自動でSNS（Bluesky）の投稿をランダムに取得・表示します。この機能を使用するにはログイン情報の設定が必要です。

- **透過表示**：キャラクターを右クリックすると半透明表示に切り替えることができます。

## テックちゃんについて

- テックちゃんは、2011年に誕生した東京工業大学の学園祭公式マスコットキャラクターです。
- テックちゃんの著作権は、東京工業大学学園祭実行委員会および原案制作者の樋田アユム氏に帰属します。
