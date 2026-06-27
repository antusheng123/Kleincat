# Klein Cat Desktop Pet

Klein Cat Desktop Pet is a lightweight PyQt6 Windows desktop pet. It displays a transparent animated black cat, supports dragging, interaction animations, brightness control, network speed display, a Todo panel, fullscreen auto-hide, and Gemini-powered short dialogue.

## Features

- Transparent frameless desktop pet window
- PNG sequence animation playback with `QTimer + QPixmap`
- Idle, interact, and scroll animation states
- Left-button drag movement
- Right-click menu with Todo panel and exit
- Mouse wheel brightness adjustment
- Network upload/download speed display
- Fullscreen app auto-hide
- Todo panel with task completion feedback
- Async Gemini dialogue through `QThread`
- Local fallback dialogue when API configuration is unavailable

## Requirements

- Windows
- Python 3.10+
- Dependencies from `requirements.txt`

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Configuration

Copy `config.example.json` to `config.json` before running if you want a local editable config.

```powershell
Copy-Item config.example.json config.json
```

Gemini API keys can be provided in either place:

- `GEMINI_API_KEY` environment variable
- `api_key` in local `config.json`

`config.json` is intentionally ignored by git so personal API keys and runtime cache are not committed.

## Run

```powershell
python main.py
```

The animation frame folders must exist next to `main.py`:

```text
idle/
interact/
scroll/
```

Each folder should contain PNG frames named like `frame_0000.png`, `frame_0001.png`, and so on.

## Project Structure

```text
main.py
requirements.txt
config.example.json
modules/
  window.py
  monitor.py
  panel.py
  llm_worker.py
idle/
interact/
scroll/
```

## Packaging

Packaging is planned for the next development phase. Build outputs such as `build/`, `dist/`, and `*.spec` are ignored by git.
