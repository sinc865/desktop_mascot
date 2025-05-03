# desktop_mascot

📄 [日本語版](./README.md)

<img src="https://github.com/user-attachments/assets/a19a4042-7e38-429e-b5bd-1141f385be3c" width="400" alt="Demo GIF">


## Features

- **Memo**: Quickly take notes to remember important ideas and tasks.
- **SNS (Bluesky) Post Display**: The character on your desktop periodically fetches and displays SNS posts. You can toggle the display as needed.
- **Transparency**: Adjust the transparency of the app to ensure it provides assistance without overwhelming your screen space.

## System Requirements
- Supported OS: Windows 10
- python 3.13

## Installation

1. Clone the repository:
    ```bash
    https://github.com/ripiripi/desktop_mascot.git
    cd desktop_mascot
    ```

2. Set up the environment using [uv](https://docs.astral.sh/uv/getting-started/installation/#__tabbed_1_1):
    ```bash
    uv venv              
    uv sync              
    ```

3. Run the application:
    ```bash
    uv run python main.py
    ```

## Usage

- **Memo**: When you start the application, a memo window appears alongside the character, allowing you to use it immediately. Notes can be edited and deleted, and are automatically saved to a text file.

- **SNS Post Display**: The mascot automatically fetches and displays random SNS posts periodically. SNS (Bluesky) login information is required for this feature.

- **Transparency**: Right-click the character to make it semi-transparent.

## About "Tech-chan" (テックちゃん)
- "Tech-chan" is the official mascot character of Tokyo Tech Festival, created in 2011. It is used as the character displayed in this application.
- The copyright of "Tech-chan" belongs to Tokyo Tech Festival executive committee and the original designer, Hida.
