from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TodoPanel(QWidget):
    task_completed = pyqtSignal(str)
    visibility_changed = pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()

        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle("每日计划")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(260, 320)

    def _setup_ui(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                color: #20292d;
                font-family: 'Microsoft YaHei UI', 'Segoe UI';
                font-size: 12px;
            }
            #PanelSurface {
                background-color: rgba(248, 244, 232, 205);
                border: 1px solid rgba(72, 57, 41, 92);
                border-radius: 10px;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 205);
                border: 1px solid rgba(72, 57, 41, 70);
                border-radius: 7px;
                padding: 6px 8px;
                selection-background-color: rgba(70, 120, 130, 130);
            }
            QPushButton {
                background-color: rgba(37, 47, 50, 218);
                color: #f8f4e8;
                border: none;
                border-radius: 7px;
                padding: 6px 10px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(57, 70, 72, 230);
            }
            QListWidget {
                background-color: rgba(255, 255, 255, 120);
                border: 1px solid rgba(72, 57, 41, 54);
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                min-height: 28px;
                padding: 4px 6px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: rgba(70, 120, 130, 78);
                color: #20292d;
            }
            """
        )

        surface = QWidget(self)
        surface.setObjectName("PanelSurface")

        self.input = QLineEdit(surface)
        self.input.setPlaceholderText("写下一件事")
        self.input.returnPressed.connect(self._add_task)

        add_button = QPushButton("添加", surface)
        add_button.clicked.connect(self._add_task)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(6)
        input_layout.addWidget(self.input, 1)
        input_layout.addWidget(add_button)

        self.task_list = QListWidget(surface)
        self.task_list.itemDoubleClicked.connect(self._complete_task)

        layout = QVBoxLayout(surface)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addLayout(input_layout)
        layout.addWidget(self.task_list, 1)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(surface)

    def _add_task(self) -> None:
        text = self.input.text().strip()
        if not text:
            return

        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.task_list.addItem(item)
        self.input.clear()

    def _complete_task(self, item: QListWidgetItem) -> None:
        if item.data(Qt.ItemDataRole.UserRole) == "done":
            return

        font = QFont(item.font())
        font.setStrikeOut(True)
        item.setFont(font)
        item.setForeground(Qt.GlobalColor.gray)
        item.setData(Qt.ItemDataRole.UserRole, "done")
        self.task_completed.emit(item.text())

    def showEvent(self, event) -> None:  # noqa: ANN001
        self.visibility_changed.emit(True)
        super().showEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.visibility_changed.emit(False)
        super().closeEvent(event)
