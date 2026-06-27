from __future__ import annotations

import time
from collections import deque

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot


class SystemMonitor(QObject):
    network_speed_changed = pyqtSignal(str)
    fullscreen_state_changed = pyqtSignal(bool)

    def __init__(
        self,
        own_window_id: int,
        network_interval_ms: int = 1000,
        fullscreen_interval_ms: int = 1200,
        network_smoothing_samples: int = 3,
    ) -> None:
        super().__init__()
        self.own_window_id = own_window_id
        self.network_interval_ms = network_interval_ms
        self.fullscreen_interval_ms = fullscreen_interval_ms
        self.network_smoothing_samples = max(1, network_smoothing_samples)
        self._previous_sent: int | None = None
        self._previous_recv: int | None = None
        self._previous_network_time: float | None = None
        self._sent_samples: deque[float] = deque(maxlen=self.network_smoothing_samples)
        self._recv_samples: deque[float] = deque(maxlen=self.network_smoothing_samples)
        self._last_fullscreen_state = False
        self._network_timer: QTimer | None = None
        self._fullscreen_timer: QTimer | None = None
        self._psutil = self._import_psutil()
        self._win32 = self._import_win32()

    @pyqtSlot()
    def start(self) -> None:
        self._network_timer = QTimer(self)
        self._network_timer.timeout.connect(self._sample_network_speed)
        self._network_timer.start(self.network_interval_ms)

        self._fullscreen_timer = QTimer(self)
        self._fullscreen_timer.timeout.connect(self._sample_fullscreen_state)
        self._fullscreen_timer.start(self.fullscreen_interval_ms)

        self._sample_network_speed()
        self._sample_fullscreen_state()

    @pyqtSlot()
    def stop(self) -> None:
        if self._network_timer is not None:
            self._network_timer.stop()
        if self._fullscreen_timer is not None:
            self._fullscreen_timer.stop()

    def _sample_network_speed(self) -> None:
        if self._psutil is None:
            return

        try:
            counters = self._psutil.net_io_counters()
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: failed to sample network speed: {exc}")
            return

        current_time = time.monotonic()
        if (
            self._previous_sent is None
            or self._previous_recv is None
            or self._previous_network_time is None
        ):
            self._previous_sent = counters.bytes_sent
            self._previous_recv = counters.bytes_recv
            self._previous_network_time = current_time
            self.network_speed_changed.emit("UP 0.0MB/s  DN 0.0MB/s")
            return

        elapsed = max(0.001, current_time - self._previous_network_time)
        sent_delta = max(0, counters.bytes_sent - self._previous_sent)
        recv_delta = max(0, counters.bytes_recv - self._previous_recv)
        self._previous_sent = counters.bytes_sent
        self._previous_recv = counters.bytes_recv
        self._previous_network_time = current_time

        self._sent_samples.append(sent_delta / elapsed)
        self._recv_samples.append(recv_delta / elapsed)
        sent_speed = sum(self._sent_samples) / len(self._sent_samples)
        recv_speed = sum(self._recv_samples) / len(self._recv_samples)

        self.network_speed_changed.emit(
            f"UP {self._format_speed(sent_speed)}  DN {self._format_speed(recv_speed)}"
        )

    def _sample_fullscreen_state(self) -> None:
        is_fullscreen = self._detect_fullscreen()
        if is_fullscreen == self._last_fullscreen_state:
            return

        self._last_fullscreen_state = is_fullscreen
        self.fullscreen_state_changed.emit(is_fullscreen)

    def _detect_fullscreen(self) -> bool:
        if self._win32 is None:
            return False

        win32gui, win32api = self._win32
        try:
            foreground = win32gui.GetForegroundWindow()
            if not foreground or foreground == self.own_window_id:
                return False

            left, top, right, bottom = win32gui.GetWindowRect(foreground)
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: failed to detect fullscreen window: {exc}")
            return False

        margin = 2
        return (
            left <= margin
            and top <= margin
            and abs((right - left) - screen_width) <= margin
            and abs((bottom - top) - screen_height) <= margin
        )

    @staticmethod
    def _format_speed(bytes_per_second: float) -> str:
        return f"{bytes_per_second / (1024 * 1024):.1f}MB/s"

    @staticmethod
    def _import_psutil():
        try:
            import psutil
        except ImportError:
            print("Warning: psutil is not installed; network speed display is disabled.")
            return None
        return psutil

    @staticmethod
    def _import_win32():
        try:
            import win32api
            import win32gui
        except ImportError:
            print("Warning: pywin32 is not installed; fullscreen auto-hide is disabled.")
            return None
        return win32gui, win32api
