# SPDX-License-Identifier: MIT
"""Reusable one-second hold button shared by the Designer controls."""
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QPushButton


class TouchButton(QPushButton):
    """Large button with a separate one-second longPressed signal.

    QPushButton.clicked keeps its standard meaning and also occurs on release
    after a long press. Connect only longPressed for hold-only actions.
    """
    longPressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(140, 64)
        self.setText('Button')
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._held)
        self.pressed.connect(self._timer.start)
        self.released.connect(self._timer.stop)

    def _held(self):
        if self.isDown() and self.isEnabled():
            self.longPressed.emit()

    def changeEvent(self, event):
        if not self.isEnabled():
            self._timer.stop()
        super().changeEvent(event)

    def focusOutEvent(self, event):
        self._timer.stop()
        super().focusOutEvent(event)

    def mouseMoveEvent(self, event):
        if not self.rect().contains(event.position().toPoint()):
            self._timer.stop()
        super().mouseMoveEvent(event)
