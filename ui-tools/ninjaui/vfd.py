# SPDX-License-Identifier: MIT
"""Hunor-style 14-segment display; see ../VFD-ORIGIN.md for source provenance."""
import math
from PySide6.QtCore import Property, Qt, QSize, Slot
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

# The web simulator's fourteen strokes, in its 24 x 32 character coordinates.
SEGMENTS = dict(zip('abcdefgmhijkln', (
    (4, 2, 16, 2), (18, 4, 18, 13), (18, 17, 18, 26), (4, 28, 16, 28),
    (2, 17, 2, 26), (2, 4, 2, 13), (4, 15, 9, 15), (11, 15, 16, 15),
    (4, 4, 9, 12), (16, 4, 11, 12), (4, 26, 9, 18), (16, 26, 11, 18),
    (10, 2, 10, 15), (10, 15, 10, 28))))
GLYPHS = {
    '0': 'abcdefij', '1': 'bc', '2': 'abdegm', '3': 'abcdgm', '4': 'bcfgm',
    '5': 'acdfgm', '6': 'acdefgm', '7': 'abc', '8': 'abcdefgm', '9': 'abcdfgm',
    'A': 'abcefgm', 'B': 'abcdmln', 'C': 'adef', 'D': 'abcdln', 'E': 'adefg',
    'F': 'aefg', 'G': 'acdefm', 'H': 'bcefgm', 'I': 'adln', 'J': 'bcde',
    'K': 'efgik', 'L': 'def', 'M': 'bcefhi', 'N': 'bcefhk', 'O': 'abcdef',
    'P': 'abefgm', 'Q': 'abcdefk', 'R': 'abefgmk', 'S': 'acdfgm', 'T': 'aln',
    'U': 'bcdef', 'V': 'efij', 'W': 'bcefjk', 'X': 'hijk', 'Y': 'hin',
    'Z': 'adij', '-': 'gm', '_': 'd', '/': 'ij', '\\': 'hk', '=': 'dgm',
    '(': 'ij', ')': 'hk', '?': 'abgmj', ':': 'adhijk', ' ': '',
    # Generic additions; ':' retains the simulator's hourglass-shaped glyph.
    '+': 'gmln', '#': 'abcdefgmhijkln',
}


def text_cells(text):
    """A point/comma follows its preceding character without consuming a cell."""
    cells = []
    for char in text.upper():
        if char in '.,':
            if cells and not cells[-1][1]:
                cells[-1] = (cells[-1][0], char)
            else:
                cells.append((' ', char))
        else:
            cells.append((char if char in GLYPHS else '?', False))
    return cells


class VfdDisplay(QWidget):
    """Hunor-style alphanumeric VFD with fourteen strokes and an independent dot."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._text, self._count = 'NINJALINUX', 18
        self._value, self._decimals, self._numeric = 0.0, 3, False
        self._separator = '.'
        self._connected, self._right, self._glow = True, False, True
        self._brightness, self._pin = 100, ''
        self._glow_radius, self._glow_strength = 6.0, 70
        self._foreground = QColor('#8effdf')
        self._background = QColor('#071415')
        self._off_color = QColor('#132e2a')
        self._cache = None
        self.setMinimumSize(48, 40)
        self.setAccessibleName('VFD display')
        self.setAccessibleDescription(self._text)

    def sizeHint(self):
        return QSize(self._count*26+16, 88)

    def _invalidate(self):
        self._cache = None
        self.setAccessibleDescription(self._text if self._connected else 'No data')
        self.update()

    def _set(self, name, value):
        if getattr(self, name) != value:
            setattr(self, name, value)
            self._invalidate()

    @Slot(str)
    def setText(self, text):
        numeric_before = self._numeric
        self._numeric = False
        self._set('_text', str(text))
        if numeric_before:
            self._invalidate()

    @Slot(float)
    def setValue(self, value):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError('VFD values must be finite')
        numeric_before = self._numeric
        self._value, self._numeric = value, True
        self._set('_text', f'{value:.{self._decimals}f}'.replace('.', self._separator))
        if not numeric_before:
            self._invalidate()

    @Slot(int)
    def setDecimals(self, value):
        self._decimals = max(0, min(6, int(value)))
        if self._numeric:
            self.setValue(self._value)

    @Slot(str)
    def setDecimalSeparator(self, value):
        if value not in ('.', ','):
            raise ValueError('Decimal separator must be a point or comma')
        self._separator = value
        if self._numeric:
            self.setValue(self._value)

    @Slot(int)
    def setCharacterCount(self, value):
        self._set('_count', max(1, min(64, int(value))))
        self.updateGeometry()

    @Slot(bool)
    def setConnected(self, value):
        self._set('_connected', bool(value))

    @Slot(bool)
    def setRightAligned(self, value):
        self._set('_right', bool(value))

    @Slot(bool)
    def setGlow(self, value):
        self._set('_glow', bool(value))

    @Slot(float)
    def setGlowRadius(self, value):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError('Glow radius must be finite')
        self._set('_glow_radius', max(0.0, min(24.0, value)))

    @Slot(int)
    def setGlowStrength(self, value):
        self._set('_glow_strength', max(0, min(100, int(value))))

    @Slot(int)
    def setBrightness(self, value):
        self._set('_brightness', max(0, min(100, int(value))))

    @Slot(str)
    def setHalPin(self, value):
        self._pin = str(value)

    def _set_color(self, name, value):
        color = QColor(value)
        if not color.isValid():
            raise ValueError('Invalid VFD color')
        self._set(name, color)

    @Slot(QColor)
    def setForegroundColor(self, value):
        self._set_color('_foreground', value)

    @Slot(QColor)
    def setBackgroundColor(self, value):
        self._set_color('_background', value)

    @Slot(QColor)
    def setOffColor(self, value):
        self._set_color('_off_color', value)

    text = Property(str, lambda s: s._text, setText)
    value = Property(float, lambda s: s._value, setValue)
    decimals = Property(int, lambda s: s._decimals, setDecimals)
    decimalSeparator = Property(str, lambda s: s._separator, setDecimalSeparator)
    characterCount = Property(int, lambda s: s._count, setCharacterCount)
    connected = Property(bool, lambda s: s._connected, setConnected)
    rightAligned = Property(bool, lambda s: s._right, setRightAligned)
    glow = Property(bool, lambda s: s._glow, setGlow)
    glowRadius = Property(float, lambda s: s._glow_radius, setGlowRadius)
    glowStrength = Property(int, lambda s: s._glow_strength, setGlowStrength)
    brightness = Property(int, lambda s: s._brightness, setBrightness)
    halPin = Property(str, lambda s: s._pin, setHalPin)
    foregroundColor = Property(QColor, lambda s: QColor(s._foreground), setForegroundColor)
    backgroundColor = Property(QColor, lambda s: QColor(s._background), setBackgroundColor)
    offColor = Property(QColor, lambda s: QColor(s._off_color), setOffColor)
    overflow = Property(bool, lambda s: len(text_cells(s._text)) > s._count)

    def displayCells(self):
        if not self._connected:
            cells = text_cells('NO DATA' if self._count >= 7 else '-'*self._count)
        elif self.overflow and self._numeric:
            cells = [('#', False)]*self._count
        else:
            cells = text_cells(self._text)[:self._count]
        padding = [(' ', False)]*(self._count-len(cells))
        return padding+cells if self._right else cells+padding

    def _draw_strokes(self, painter, color, width, active_only):
        cell_width = max(1, self.width()-16)/self._count
        scale = min(cell_width/24, max(1, self.height()-16)/32)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for index, (char, dot) in enumerate(self.displayCells()):
            painter.save()
            painter.translate(8+index*cell_width+(cell_width-24*scale)/2, (self.height()-32*scale)/2)
            painter.scale(scale, scale)
            painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for name, (x1, y1, x2, y2) in SEGMENTS.items():
                if not active_only or name in GLYPHS[char]:
                    painter.drawLine(x1, y1, x2, y2)
            if not active_only or dot:
                painter.drawEllipse(21, 28, 2, 2)
                if dot == ',':
                    painter.drawLine(22, 30, 21, 32)
            painter.restore()

    @staticmethod
    def _soften(image, radius):
        # Two smooth resamples approximate a soft bloom in native Qt code.
        # No Python pixel loops, graphics scene or continuously running effect.
        divisor = max(1.0, radius*image.devicePixelRatioF())
        small = image.scaled(max(1, round(image.width()/divisor)),
                             max(1, round(image.height()/divisor)),
                             Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        return small.scaled(image.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)

    def _render(self, pixmap):
        painter = QPainter(pixmap)
        painter.fillRect(self.rect(), self._background)
        painter.setPen(QColor('#3d4a3d'))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        self._draw_strokes(painter, self._off_color, 1.8, False)
        lit = QColor(self._foreground if self._connected else '#81958f')
        lit.setAlphaF(self._brightness/100)
        bloom = self._glow and self._glow_radius > 0 and self._glow_strength > 0
        if bloom:
            emitter = QPixmap(pixmap.size())
            emitter.setDevicePixelRatio(pixmap.devicePixelRatioF())
            emitter.fill(Qt.GlobalColor.transparent)
            light = QPainter(emitter)
            self._draw_strokes(light, lit, 1.8, True)
            light.end()
            strength = self._glow_strength/100
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            for radius, opacity in ((self._glow_radius*2, .65), (self._glow_radius/2, 1.0)):
                painter.setOpacity(strength*opacity)
                painter.drawPixmap(0, 0, self._soften(emitter, radius))
            painter.setOpacity(1.0)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        self._draw_strokes(painter, lit, 1.8, True)
        if bloom:
            # A narrow, paler phosphor core gives the strokes depth without
            # brightening unlit segments. Brightness=0 also extinguishes this.
            core = QColor(lit)
            core.setRedF(core.redF()*.48+.52)
            core.setGreenF(core.greenF()*.48+.52)
            core.setBlueF(core.blueF()*.48+.52)
            core.setAlphaF(lit.alphaF()*.65*self._glow_strength/100)
            self._draw_strokes(painter, core, .65, True)
        painter.end()

    def paintEvent(self, event):
        dpr = self.devicePixelRatioF()
        size = QSize(max(1, round(self.width()*dpr)), max(1, round(self.height()*dpr)))
        if self._cache is None or self._cache.size() != size or self._cache.devicePixelRatioF() != dpr:
            self._cache = QPixmap(size)
            self._cache.setDevicePixelRatio(dpr)
            self._cache.fill(self._background)
            self._render(self._cache)
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cache)
