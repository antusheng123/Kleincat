from __future__ import annotations

import json
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from modules.window import PetWindow


DEFAULT_CONFIG = {
    "base_size": 200,
    "animation_fps": 40,
    "brightness_step": 5,
    "llm_provider": "gemini",
    "api_key": "",
    "model": "gemini-2.5-flash-lite",
    "show_network_speed": True,
    "todo_panel_visible": False,
    "enable_fullscreen_auto_hide": True,
    "network_smoothing_samples": 3,
    "last_fortune_date": "",
    "last_fortune_result": None,
    "animation_dirs": {
        "idle": "idle",
        "interact": "interact",
        "scroll": "scroll",
    },
}


def load_config(project_root: Path) -> dict:
    config_path = project_root / "config.json"
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with config_path.open("r", encoding="utf-8") as file:
            loaded_config = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: failed to read config.json, using defaults: {exc}")
        return DEFAULT_CONFIG.copy()

    config = DEFAULT_CONFIG.copy()
    config.update(loaded_config)
    config["animation_dirs"] = {
        **DEFAULT_CONFIG["animation_dirs"],
        **loaded_config.get("animation_dirs", {}),
    }
    return config


def main() -> int:
    project_root = Path(__file__).resolve().parent
    app = QApplication(sys.argv)

    window = PetWindow(project_root=project_root, config=load_config(project_root))
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
