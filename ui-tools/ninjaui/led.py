# SPDX-License-Identifier: MIT
"""Text/icon widgets with an independent, cached status LED. No hardware access."""
import math
from PySide6.QtCore import Property, Qt, QRectF, QSize, Slot
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget, QLabel, QStyle, QStyleOptionButton, QStylePainter
from .glow import soften


class _GlowLamp(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.active, self.connected, self.glow = False, True, True
        self.color, self.off_color = QColor('#22e5ac'), QColor('#18332c')
        self.radius, self.strength, self.brightness, self.diameter = 5.0, 70, 100, 18
        self._cache = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet('background: transparent; border: none;')

    def set_state(self, name, value):
        if getattr(self, name) != value:
            setattr(self, name, value)
            self._cache = None
            self.update()

    def extent(self):
        return self.diameter+2*(math.ceil(self.radius*2)+2)

    def _render(self, pixmap):
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        circle = QRectF((self.width()-self.diameter)/2, (self.height()-self.diameter)/2, self.diameter, self.diameter)
        painter.setPen(QPen(QColor('#41645b'), 1))
        painter.setBrush(self.off_color if self.connected else QColor('#374151'))
        painter.drawEllipse(circle)
        if self.active and self.connected and self.brightness:
            lit = QColor(self.color); lit.setAlphaF(self.brightness/100)
            emitter = QPixmap(pixmap.size())
            emitter.setDevicePixelRatio(pixmap.devicePixelRatioF())
            emitter.fill(Qt.GlobalColor.transparent)
            light = QPainter(emitter)
            light.setRenderHint(QPainter.RenderHint.Antialiasing)
            light.setPen(Qt.PenStyle.NoPen); light.setBrush(lit)
            light.drawEllipse(circle.adjusted(1, 1, -1, -1)); light.end()
            if self.glow and self.radius and self.strength:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
                for radius, opacity in ((self.radius*2, .65), (self.radius/2, 1.0)):
                    painter.setOpacity(self.strength/100*opacity)
                    painter.drawPixmap(0, 0, soften(emitter, radius))
                painter.setOpacity(1)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, emitter)
            # A brighter lens center keeps the lamp distinct from a flat disk.
            core = QRadialGradient(circle.center(), self.diameter/2)
            pale = QColor(lit.lighter(150)); pale.setAlphaF(lit.alphaF()*.7)
            core.setColorAt(0, pale)
            clear = QColor(lit); clear.setAlpha(0)
            core.setColorAt(1, clear)
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(core)
            painter.drawEllipse(circle.adjusted(1, 1, -1, -1))
        elif not self.connected:
            painter.setPen(QColor('#f1f5f9'))
            font = painter.font(); font.setPixelSize(max(8, self.diameter-4)); painter.setFont(font)
            painter.drawText(circle, Qt.AlignmentFlag.AlignCenter, '?')
        painter.end()

    def paintEvent(self, event):
        dpr = self.devicePixelRatioF()
        size = QSize(max(1, round(self.width()*dpr)), max(1, round(self.height()*dpr)))
        if self._cache is None or self._cache.size() != size or self._cache.devicePixelRatioF() != dpr:
            self._cache = QPixmap(size); self._cache.setDevicePixelRatio(dpr)
            self._cache.fill(Qt.GlobalColor.transparent)
            self._render(self._cache)
        painter = QPainter(self); painter.drawPixmap(0, 0, self._cache)


class _LedHost:
    """Geometry/state helpers; public Qt properties are declared on each widget."""
    def _init_led(self):
        self._lamp, self._led_right, self._hal_pin = _GlowLamp(self), True, ''
        self.setMinimumHeight(64)
        self._place_led()

    def _reserve(self):
        return self._lamp.extent()+20

    def _place_led(self):
        extent = self._lamp.extent()
        self.setMinimumHeight(max(self.minimumHeight(), 64, extent+4))
        x = self.width()-extent-10 if self._led_right else 10
        self._lamp.setGeometry(x, (self.height()-extent)//2, extent, extent)
        self._lamp.raise_()
        if isinstance(self, QLabel):
            self.setContentsMargins(12 if self._led_right else self._reserve(), 8,
                                    self._reserve() if self._led_right else 12, 8)
        self.updateGeometry()
        self.update()

    def _set_color(self, name, value):
        value = QColor(value)
        if not value.isValid():
            raise ValueError('Invalid LED color')
        self._lamp.set_state(name, value)

    def _set_radius(self, value):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError('LED glow radius must be finite')
        self._lamp.set_state('radius', max(0.0, min(24.0, value)))
        self._place_led()


from .touch import TouchButton


class LedButton(TouchButton, _LedHost):
    """Touch button with PNG/Unicode content and an independent glowing LED."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._follow_button = True
        self._init_led()
        self.setText('LED button')
        self.setCheckable(True)
        self.toggled.connect(self._follow_state)
        self.pressed.connect(self._follow_state)
        self.released.connect(self._follow_state)

    def _follow_state(self, *args):
        if self._follow_button:
            self.setActive(self.isChecked() if self.isCheckable() else (self.isDown() and self.isEnabled()))

    @Slot(bool)
    def setFollowButton(self, value):
        self._follow_button = bool(value)
        self._follow_state()

    followButton = Property(bool, lambda s: s._follow_button, setFollowButton)

    @Slot(bool)
    def setActive(self, value):
        self._lamp.set_state('active', bool(value))

    @Slot(bool)
    def setConnected(self, value):
        self._lamp.set_state('connected', bool(value))

    @Slot(bool)
    def setGlow(self, value):
        self._lamp.set_state('glow', bool(value))

    @Slot(float)
    def setGlowRadius(self, value):
        self._set_radius(value)

    @Slot(int)
    def setGlowStrength(self, value):
        self._lamp.set_state('strength', max(0, min(100, int(value))))

    @Slot(int)
    def setBrightness(self, value):
        self._lamp.set_state('brightness', max(0, min(100, int(value))))

    @Slot(int)
    def setLedDiameter(self, value):
        self._lamp.set_state('diameter', max(6, min(48, int(value))))
        self._place_led()

    @Slot(bool)
    def setLedOnRight(self, value):
        self._led_right = bool(value)
        self._place_led()

    @Slot(QColor)
    def setLedColor(self, value):
        self._set_color('color', value)

    @Slot(QColor)
    def setOffColor(self, value):
        self._set_color('off_color', value)

    @Slot(str)
    def setHalPin(self, value):
        self._hal_pin = str(value)

    active = Property(bool, lambda s: s._lamp.active, setActive)
    connected = Property(bool, lambda s: s._lamp.connected, setConnected)
    glow = Property(bool, lambda s: s._lamp.glow, setGlow)
    glowRadius = Property(float, lambda s: s._lamp.radius, setGlowRadius)
    glowStrength = Property(int, lambda s: s._lamp.strength, setGlowStrength)
    brightness = Property(int, lambda s: s._lamp.brightness, setBrightness)
    ledDiameter = Property(int, lambda s: s._lamp.diameter, setLedDiameter)
    ledOnRight = Property(bool, lambda s: s._led_right, setLedOnRight)
    ledColor = Property(QColor, lambda s: QColor(s._lamp.color), setLedColor)
    offColor = Property(QColor, lambda s: QColor(s._lamp.off_color), setOffColor)
    halPin = Property(str, lambda s: s._hal_pin, setHalPin)

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, '_lamp'):
            self._follow_state()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self._follow_button and not self.isCheckable():
            self.setActive(False)

    def sizeHint(self):
        hint = super().sizeHint()
        return QSize(hint.width()+self._reserve(), max(hint.height(), self._lamp.extent()+4, 64))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_led()

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionButton(); self.initStyleOption(option)
        background = QStyleOptionButton(option)
        background.text, background.icon = '', QIcon()
        painter.drawControl(QStyle.ControlElement.CE_PushButton, background)
        content = self.style().subElementRect(QStyle.SubElement.SE_PushButtonContents, option, self)
        option.rect = content.adjusted(0 if self._led_right else self._reserve(), 0,
                                       -self._reserve() if self._led_right else 0, 0)
        painter.drawControl(QStyle.ControlElement.CE_PushButtonLabel, option)


class LedLabel(QLabel, _LedHost):
    """Standard Unicode-capable label with an independent glowing status LED."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_led()
        self.setText('LED label')
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

    @Slot(bool)
    def setActive(self, value):
        self._lamp.set_state('active', bool(value))

    @Slot(bool)
    def setConnected(self, value):
        self._lamp.set_state('connected', bool(value))

    @Slot(bool)
    def setGlow(self, value):
        self._lamp.set_state('glow', bool(value))

    @Slot(float)
    def setGlowRadius(self, value):
        self._set_radius(value)

    @Slot(int)
    def setGlowStrength(self, value):
        self._lamp.set_state('strength', max(0, min(100, int(value))))

    @Slot(int)
    def setBrightness(self, value):
        self._lamp.set_state('brightness', max(0, min(100, int(value))))

    @Slot(int)
    def setLedDiameter(self, value):
        self._lamp.set_state('diameter', max(6, min(48, int(value))))
        self._place_led()

    @Slot(bool)
    def setLedOnRight(self, value):
        self._led_right = bool(value)
        self._place_led()

    @Slot(QColor)
    def setLedColor(self, value):
        self._set_color('color', value)

    @Slot(QColor)
    def setOffColor(self, value):
        self._set_color('off_color', value)

    @Slot(str)
    def setHalPin(self, value):
        self._hal_pin = str(value)

    active = Property(bool, lambda s: s._lamp.active, setActive)
    connected = Property(bool, lambda s: s._lamp.connected, setConnected)
    glow = Property(bool, lambda s: s._lamp.glow, setGlow)
    glowRadius = Property(float, lambda s: s._lamp.radius, setGlowRadius)
    glowStrength = Property(int, lambda s: s._lamp.strength, setGlowStrength)
    brightness = Property(int, lambda s: s._lamp.brightness, setBrightness)
    ledDiameter = Property(int, lambda s: s._lamp.diameter, setLedDiameter)
    ledOnRight = Property(bool, lambda s: s._led_right, setLedOnRight)
    ledColor = Property(QColor, lambda s: QColor(s._lamp.color), setLedColor)
    offColor = Property(QColor, lambda s: QColor(s._lamp.off_color), setOffColor)
    halPin = Property(str, lambda s: s._hal_pin, setHalPin)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_led()
