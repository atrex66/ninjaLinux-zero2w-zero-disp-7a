# SPDX-License-Identifier: MIT
"""Designer-friendly widgets. No network, HAL, or output side effects."""
import math
from PySide6.QtCore import Property, Qt, Signal, Slot, QSize
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QGridLayout


class StatusLed(QWidget):
    """A read-only status indicator with an optional external HAL pin name."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active, self._connected, self._pin = False, True, ''
        self.setMinimumSize(40, 40)

    def sizeHint(self):
        return QSize(48, 48)

    @Slot(bool)
    def setActive(self, value):
        self._active = bool(value)
        self.update()

    @Slot(bool)
    def setConnected(self, value):
        self._connected = bool(value)
        self.update()

    @Slot(str)
    def setHalPin(self, value):
        self._pin = value

    active = Property(bool, lambda s: s._active, setActive)
    connected = Property(bool, lambda s: s._connected, setConnected)
    halPin = Property(str, lambda s: s._pin, lambda s, v: setattr(s, '_pin', v))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = '#64748b' if not self._connected else ('#22c55e' if self._active else '#263747')
        painter.setBrush(QColor(color))
        painter.setPen(QColor('#94a3b8'))
        diameter = min(self.width(), self.height()) - 12
        painter.drawEllipse((self.width()-diameter)//2, (self.height()-diameter)//2, diameter, diameter)
        if not self._connected:
            painter.setPen(QColor('#f8fafc'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, '?')


class AxisDisplay(QLabel):
    """Generic numeric readout: no coordinate system or tool-offset logic."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value, self._decimals = 0.0, 3
        self._axis, self._suffix, self._pin, self._connected = 'A', 'mm', '', True
        self.setMinimumHeight(110)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self.setFont(QFont('DejaVu Sans', 42, QFont.Weight.Bold))
        self._refresh()

    def _refresh(self):
        value = f'{self._value:.{self._decimals}f}' if self._connected else '—'
        self.setText(f'{self._axis}   {value} {self._suffix}')

    @Slot(float)
    def setValue(self, value):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError('Display values must be finite')
        self._value = value
        self._refresh()

    @Slot(bool)
    def setConnected(self, value):
        self._connected = bool(value)
        self._refresh()

    def _set(self, name, value):
        setattr(self, name, value)
        self._refresh()

    @Slot(str)
    def setAxisLabel(self, value):
        self._set('_axis', value)

    @Slot(str)
    def setSuffix(self, value):
        self._set('_suffix', value)

    @Slot(int)
    def setDecimals(self, value):
        self._set('_decimals', max(0, min(6, value)))

    @Slot(str)
    def setHalPin(self, value):
        self._pin = value

    value = Property(float, lambda s: s._value, setValue)
    decimals = Property(int, lambda s: s._decimals, lambda s, v: s._set('_decimals', max(0, min(6, v))))
    axisLabel = Property(str, lambda s: s._axis, lambda s, v: s._set('_axis', v))
    suffix = Property(str, lambda s: s._suffix, lambda s, v: s._set('_suffix', v))
    connected = Property(bool, lambda s: s._connected, setConnected)
    halPin = Property(str, lambda s: s._pin, lambda s, v: setattr(s, '_pin', v))


class NumericPad(QWidget):
    """Embedded decimal input; emits a value without writing any machine state."""
    accepted = Signal(float)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setSpacing(8)
        self.entry = QLineEdit('0', self)
        self.entry.setReadOnly(True)
        self.entry.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.entry.setMinimumHeight(64)
        self.entry.setFont(QFont('DejaVu Sans', 26))
        layout.addWidget(self.entry, 0, 0, 1, 4)
        for index, text in enumerate(('7', '8', '9', '⌫', '4', '5', '6', 'C', '1', '2', '3', '±', '0', '.', 'Cancel', 'OK')):
            button = QPushButton(text, self)
            button.setMinimumSize(80, 64)
            button.clicked.connect(lambda checked=False, key=text: self.inputKey(key))
            layout.addWidget(button, 1+index//4, index%4)

    @Slot(str)
    def inputKey(self, key):
        text = self.entry.text()
        if key == 'Cancel':
            self.cancelled.emit()
            return
        if key == 'OK':
            try:
                number = float(text)
                if math.isfinite(number):
                    self.accepted.emit(number)
            except ValueError:
                pass
            return
        if key == 'C':
            text = '0'
        elif key == '⌫':
            text = text[:-1] or '0'
        elif key == '±':
            text = text[1:] if text.startswith('-') else '-'+text
        elif key == '.':
            if '.' not in text:
                text += '.'
        elif key in '0123456789' and len(key) == 1:
            if text in ('0', '-0'):
                text = ('-' if text.startswith('-') else '') + key
            elif len(text) < 16:
                text += key
        self.entry.setText(text)

    @Slot(float)
    def setValue(self, value):
        if not math.isfinite(float(value)):
            raise ValueError('Input values must be finite')
        self.entry.setText(format(float(value), '.12g'))

    value = Property(float, lambda s: float(s.entry.text()) if s.entry.text() not in ('-', '-.', '.') else 0.0, setValue)


# Re-export keeps one stable Designer/uic header for the entire widget group.
from .vfd import VfdDisplay

from .touch import TouchButton
from .led import LedButton, LedLabel
