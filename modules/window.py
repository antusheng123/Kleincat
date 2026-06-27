from __future__ import annotations

import json
import os
import random
from datetime import date
from pathlib import Path

from PyQt6.QtCore import QMetaObject, QPoint, QRectF, Qt, QThread, QTimer
from PyQt6.QtGui import (
    QAction,
    QColor,
    QCloseEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtWidgets import QLabel, QMenu, QWidget

from modules.llm_worker import LLMWorker
from modules.monitor import SystemMonitor
from modules.panel import TodoPanel


class AnimationState:
    IDLE = "idle"
    INTERACT = "interact"
    SCROLL = "scroll"


SYSTEM_PROMPT = (
    "你现在是小说《诡秘之主》的主角克莱恩·莫雷蒂，"
    "变成了一只戴黑礼帽的小黑猫，常驻在主人的桌面上。"
    "你冷静、优雅、克制，但内心很会吐槽。"
    "你只能输出 JSON，不要输出 Markdown、解释或额外字段。"
    "JSON 格式必须是 {\"dialogue\":\"台词\"}。"
    "台词必须是中文，不超过 25 个汉字，末尾不要句号。"
)

FORTUNE_POOL = [
    {
        "card": "愚者",
        "orientation": "正位",
        "good": "整理计划",
        "bad": "冲动提交代码",
        "lucky_time": "09:30",
    },
    {
        "card": "倒吊人",
        "orientation": "逆位",
        "good": "摸鱼五分钟",
        "bad": "硬改不懂的模块",
        "lucky_time": "15:30",
    },
    {
        "card": "星星",
        "orientation": "正位",
        "good": "写测试",
        "bad": "熬夜赶工",
        "lucky_time": "20:00",
    },
    {
        "card": "隐者",
        "orientation": "正位",
        "good": "安静 debug",
        "bad": "群聊争论架构",
        "lucky_time": "11:11",
    },
]

LOCAL_FALLBACK_DIALOGUES = [
    "命运暂时保持沉默。",
    "赞美愚者，接口迷路了。",
    "这很合理，也很神秘。",
    "先别慌，猫会观察。",
]


class SpeechBubbleLabel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(168, 62)
        self._text = ""

    def setText(self, text: str) -> None:  # noqa: N802
        self._text = text
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        path = QPainterPath()
        bubble_rect = QRectF(12, 2, self.width() - 16, self.height() - 11)
        path.addRoundedRect(bubble_rect, 17, 17)

        tail = QPainterPath()
        tail.moveTo(29, self.height() - 21)
        tail.lineTo(4, self.height() - 8)
        tail.lineTo(42, self.height() - 15)
        tail.closeSubpath()
        path = path.united(tail)

        shadow = QPainterPath(path)
        shadow.translate(0, 2)
        painter.fillPath(shadow, QColor(0, 0, 0, 28))

        painter.fillPath(path, QColor(255, 252, 244, 242))
        painter.setPen(QPen(QColor(45, 52, 52, 54), 1))
        painter.drawPath(path)

        font = painter.font()
        font.setFamily("Segoe Print")
        font.setPointSize(9)
        font.setWeight(400)
        painter.setFont(font)
        painter.setPen(QColor(36, 43, 45))
        text_rect = bubble_rect.adjusted(13, 6, -13, -7)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self._text,
        )


class PetWindow(QWidget):
    def __init__(self, project_root: Path, config: dict) -> None:
        super().__init__()

        self.project_root = project_root
        self.config = config
        self.base_size = int(config.get("base_size", 200))
        self.animation_fps = max(1, int(config.get("animation_fps", 12)))
        self.brightness_step = max(1, int(config.get("brightness_step", 5)))
        self.show_network_speed = bool(config.get("show_network_speed", True))
        self.enable_fullscreen_auto_hide = bool(config.get("enable_fullscreen_auto_hide", True))
        self.network_smoothing_samples = max(1, int(config.get("network_smoothing_samples", 3)))
        self.todo_panel_visible = bool(config.get("todo_panel_visible", False))
        self.animation_dirs = config.get("animation_dirs", {})

        self.current_state = AnimationState.IDLE
        self.current_frame_index = 0
        self.drag_offset: QPoint | None = None
        self.monitor_thread: QThread | None = None
        self.monitor: SystemMonitor | None = None
        self.todo_panel: TodoPanel | None = None
        self.llm_thread: QThread | None = None
        self.llm_worker: LLMWorker | None = None
        self.dialogue_visible = False
        self.frames: dict[str, list[QPixmap]] = {
            AnimationState.IDLE: [],
            AnimationState.INTERACT: [],
            AnimationState.SCROLL: [],
        }

        self._setup_window()
        self._load_frames()
        self._setup_timer()
        self._setup_monitor()
        self._setup_todo_panel()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setFixedSize(self._window_width(), self._window_height())

        self.sprite_label = QLabel(self)
        self.sprite_label.setFixedSize(self.base_size, self.base_size)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sprite_label.move(0, 0)

        self.dialogue_label = SpeechBubbleLabel(self)
        self.dialogue_label.hide()

        network_label_width = min(160, self.base_size - 8)
        self.network_label = QLabel(self)
        self.network_label.setFixedSize(network_label_width, 24)
        self.network_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.network_label.setText("UP 0.0MB/s  DN 0.0MB/s")
        self.network_label.setStyleSheet(
            "QLabel {"
            " color: #1f2b2d;"
            " background-color: rgba(248, 244, 232, 188);"
            " border: 1px solid rgba(72, 57, 41, 88);"
            " border-radius: 9px;"
            " font-family: 'Segoe Print', 'Comic Sans MS', 'Microsoft YaHei UI';"
            " font-size: 10px;"
            " font-weight: 700;"
            "}"
        )
        self.network_label.setVisible(self.show_network_speed)

        self.dialogue_timer = QTimer(self)
        self.dialogue_timer.setSingleShot(True)
        self.dialogue_timer.timeout.connect(self._hide_dialogue)
        self._relayout_overlays()

    def _load_frames(self) -> None:
        for state in self.frames:
            self.frames[state] = self._load_state_frames(state)

        if not self.frames[AnimationState.IDLE]:
            print(
                "Error: idle animation frames were not found. "
                "Expected PNG files like idle/frame_0000.png."
            )
            return

        for state in (AnimationState.INTERACT, AnimationState.SCROLL):
            if not self.frames[state]:
                print(f"Warning: {state} frames missing; falling back to idle animation.")
                self.frames[state] = self.frames[AnimationState.IDLE]

        self.sprite_label.setPixmap(self.frames[AnimationState.IDLE][0])

    def _load_state_frames(self, state: str) -> list[QPixmap]:
        configured_dir = self.animation_dirs.get(state, state)
        frame_dir = Path(configured_dir)
        if not frame_dir.is_absolute():
            frame_dir = self.project_root / frame_dir

        if not frame_dir.exists():
            print(f"Warning: animation directory does not exist: {frame_dir}")
            return []

        frame_paths = sorted(frame_dir.glob("frame_*.png"))
        if not frame_paths:
            print(f"Warning: no frame_*.png files found in: {frame_dir}")
            return []

        frames: list[QPixmap] = []
        for frame_path in frame_paths:
            pixmap = QPixmap(str(frame_path))
            if pixmap.isNull():
                print(f"Warning: failed to load frame: {frame_path}")
                continue

            frames.append(
                pixmap.scaled(
                    self.base_size,
                    self.base_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        return frames

    def _setup_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance_frame)
        self.timer.start(round(1000 / self.animation_fps))

    def _setup_monitor(self) -> None:
        if not self.show_network_speed and not self.enable_fullscreen_auto_hide:
            return

        self.monitor_thread = QThread(self)
        self.monitor = SystemMonitor(
            own_window_id=int(self.winId()),
            network_smoothing_samples=self.network_smoothing_samples,
        )
        self.monitor.moveToThread(self.monitor_thread)
        self.monitor_thread.started.connect(self.monitor.start)
        self.monitor.network_speed_changed.connect(self._set_network_speed)
        self.monitor.fullscreen_state_changed.connect(self._set_fullscreen_hidden)
        self.monitor_thread.start()

    def _setup_todo_panel(self) -> None:
        self.todo_panel = TodoPanel()
        self.todo_panel.task_completed.connect(self._handle_task_completed)
        self.todo_panel.visibility_changed.connect(self._set_todo_panel_visible)

        if self.todo_panel_visible:
            self._show_todo_panel()

    def _advance_frame(self) -> None:
        frames = self.frames.get(self.current_state) or self.frames[AnimationState.IDLE]
        if not frames:
            return

        self.sprite_label.setPixmap(frames[self.current_frame_index])
        self.current_frame_index += 1

        if self.current_frame_index >= len(frames):
            if self.current_state == AnimationState.IDLE:
                self.current_frame_index = 0
            else:
                self._switch_animation(AnimationState.IDLE)

    def _switch_animation(self, state: str) -> None:
        if state == AnimationState.SCROLL and self.current_state == AnimationState.INTERACT:
            return

        frames = self.frames.get(state)
        if not frames:
            state = AnimationState.IDLE

        self.current_state = state
        self.current_frame_index = 0
        self.setFixedSize(self._window_width(), self._window_height())
        self.sprite_label.setFixedSize(self.base_size, self.base_size)
        self._relayout_overlays()

    def _window_width(self) -> int:
        if self.dialogue_visible:
            return self.base_size + 128
        return self.base_size

    def _window_height(self) -> int:
        height = self.base_size
        if self.show_network_speed:
            height += 32
        return height

    def _relayout_overlays(self) -> None:
        if self.dialogue_visible:
            self.dialogue_label.move(self.base_size - 48, 14)

        network_label_width = self.network_label.width()
        self.network_label.move((self.base_size - network_label_width) // 2, self.base_size + 4)

    def _set_network_speed(self, text: str) -> None:
        if self.show_network_speed:
            self.network_label.setText(text)

    def _show_dialogue(self, text: str, duration_ms: int = 5200) -> None:
        self.dialogue_visible = True
        self.dialogue_label.setText(self._clean_dialogue_text(text))
        self.dialogue_label.show()
        self.setFixedSize(self._window_width(), self._window_height())
        self._relayout_overlays()
        self._position_todo_panel()
        self.dialogue_timer.start(duration_ms)

    def _hide_dialogue(self) -> None:
        self.dialogue_visible = False
        self.dialogue_label.hide()
        self.setFixedSize(self._window_width(), self._window_height())
        self._relayout_overlays()
        self._position_todo_panel()

    @staticmethod
    def _clean_dialogue_text(text: str) -> str:
        return text.strip().rstrip("。.!！?？~～…，,、；;：:")

    def _set_fullscreen_hidden(self, hidden: bool) -> None:
        if not self.enable_fullscreen_auto_hide:
            return

        if hidden:
            self.hide()
        else:
            self.show()

    def _set_todo_panel_visible(self, visible: bool) -> None:
        self.todo_panel_visible = visible

    def _show_todo_panel(self) -> None:
        if self.todo_panel is None:
            return

        if not self.todo_panel.isVisible():
            self._position_todo_panel()
            self.todo_panel.show()
        self.todo_panel.raise_()
        self.todo_panel.activateWindow()

    def _position_todo_panel(self) -> None:
        if self.todo_panel is None:
            return

        panel_x = self.x() + self._window_width() + 8
        panel_y = self.y()
        self.todo_panel.move(panel_x, panel_y)

    def _toggle_todo_panel(self, checked: bool) -> None:
        if self.todo_panel is None:
            return

        if checked:
            self._show_todo_panel()
        else:
            self.todo_panel.close()

    def _handle_task_completed(self, _task_text: str) -> None:
        self._switch_animation(AnimationState.INTERACT)
        prompt = self._build_task_prompt(_task_text)
        self._request_dialogue(prompt)

    def _draw_today_fortune(self) -> dict:
        today = date.today().isoformat()
        cached_date = self.config.get("last_fortune_date")
        cached_result = self.config.get("last_fortune_result")
        if cached_date == today and isinstance(cached_result, dict):
            return cached_result

        fortune = random.choice(FORTUNE_POOL).copy()
        self.config["last_fortune_date"] = today
        self.config["last_fortune_result"] = fortune
        self._save_config()
        return fortune

    def _build_fortune_prompt(self, fortune: dict) -> str:
        fortune_text = (
            f"主人抽到了{fortune['card']}{fortune['orientation']}，"
            f"今日宜{fortune['good']}，忌{fortune['bad']}，"
            f"幸运时间是{fortune['lucky_time']}。"
        )
        return (
            f"{SYSTEM_PROMPT}\n"
            f"请根据以下今日运势，用克莱恩小黑猫的语气包装成一句短台词：{fortune_text}"
        )

    def _local_fortune_dialogue(self, fortune: dict) -> str:
        return f"今日宜{fortune['good']}。"

    def _build_task_prompt(self, task_text: str) -> str:
        return (
            f"{SYSTEM_PROMPT}\n"
            f"主人刚完成了任务：{task_text}。"
            "请用克莱恩小黑猫的语气给一句简短反馈。"
        )

    def _request_dialogue(self, prompt: str, fallback: str | None = None) -> None:
        api_key = self._load_gemini_api_key()
        model = str(self.config.get("model", "gemini-2.5-flash-lite")).strip()
        provider = str(self.config.get("llm_provider", "gemini")).strip().lower()
        fallback_dialogue = fallback or random.choice(LOCAL_FALLBACK_DIALOGUES)

        if provider != "gemini" or not api_key or not model:
            print(
                "Gemini skipped: "
                f"provider={provider!r}, key_present={bool(api_key)}, model={model!r}"
            )
            self._show_dialogue(fallback_dialogue)
            return

        if self.llm_thread is not None and self.llm_thread.isRunning():
            self._show_dialogue("命运还在思考。")
            return

        print(f"Gemini request started: model={model}")
        self.llm_thread = QThread(self)
        self.llm_worker = LLMWorker(api_key=api_key, model=model, prompt=prompt)
        self.llm_worker.moveToThread(self.llm_thread)
        self.llm_thread.started.connect(self.llm_worker.run)
        self.llm_worker.finished.connect(self._handle_llm_finished)
        self.llm_worker.failed.connect(lambda message: self._handle_llm_failed(message, fallback_dialogue))
        self.llm_worker.finished.connect(self.llm_thread.quit)
        self.llm_worker.failed.connect(self.llm_thread.quit)
        self.llm_worker.finished.connect(self.llm_worker.deleteLater)
        self.llm_worker.failed.connect(self.llm_worker.deleteLater)
        self.llm_thread.finished.connect(self._clear_llm_thread)
        self.llm_thread.start()

    def _load_gemini_api_key(self) -> str:
        api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"')
        if api_key:
            return api_key

        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value, _value_type = winreg.QueryValueEx(key, "GEMINI_API_KEY")
            api_key = str(value).strip().strip('"')
        except Exception:  # noqa: BLE001
            api_key = ""

        return api_key or str(self.config.get("api_key", "")).strip().strip('"')

    def _handle_llm_finished(self, dialogue: str) -> None:
        print("Gemini request finished.")
        self._show_dialogue(dialogue)

    def _handle_llm_failed(self, message: str, fallback: str) -> None:
        print(f"Warning: LLM request failed: {message}")
        self._show_dialogue(fallback)

    def _clear_llm_thread(self) -> None:
        if self.llm_thread is not None:
            self.llm_thread.deleteLater()
        self.llm_thread = None
        self.llm_worker = None

    def _save_config(self) -> None:
        config_path = self.project_root / "config.json"
        try:
            with config_path.open("w", encoding="utf-8") as file:
                json.dump(self.config, file, ensure_ascii=False, indent=2)
                file.write("\n")
        except OSError as exc:
            print(f"Warning: failed to save config.json: {exc}")

    def _adjust_brightness(self, wheel_delta: int) -> None:
        if wheel_delta == 0:
            return

        try:
            import screen_brightness_control as sbc

            brightness = sbc.get_brightness()
            current = brightness[0] if isinstance(brightness, list) else brightness
            target = max(0, min(100, int(current) + self.brightness_step * (1 if wheel_delta > 0 else -1)))
            sbc.set_brightness(target)
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: failed to adjust screen brightness: {exc}")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def moveEvent(self, event) -> None:  # noqa: ANN001
        self._position_todo_panel()
        super().moveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = None
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._switch_animation(AnimationState.INTERACT)
            fortune = self._draw_today_fortune()
            self._request_dialogue(self._build_fortune_prompt(fortune), self._local_fortune_dialogue(fortune))
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        self._switch_animation(AnimationState.SCROLL)
        self._adjust_brightness(event.angleDelta().y())
        event.accept()

    def contextMenuEvent(self, event) -> None:  # noqa: ANN001
        menu = QMenu(self)
        todo_action = QAction("每日计划", self)
        todo_action.setCheckable(True)
        todo_action.setChecked(self.todo_panel_visible)
        todo_action.toggled.connect(self._toggle_todo_panel)
        menu.addAction(todo_action)
        menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)
        menu.exec(event.globalPos())

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.todo_panel is not None:
            self.todo_panel.close()

        if self.monitor is not None and self.monitor_thread is not None:
            if self.monitor_thread.isRunning():
                QMetaObject.invokeMethod(
                    self.monitor,
                    "stop",
                    Qt.ConnectionType.BlockingQueuedConnection,
                )
                self.monitor_thread.quit()
                self.monitor_thread.wait(1500)

        super().closeEvent(event)
