# SPDX-License-Identifier: MIT
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from ninjaui.widgets import VfdDisplay
from ninjaui.vfd import GLYPHS, SEGMENTS, text_cells
from ninjaui.hal_reader import HalReader

APP = QApplication.instance() or QApplication([])


class VfdTests(unittest.TestCase):
    def test_point_and_comma_are_independent_of_character_width(self):
        self.assertEqual(text_cells('a1,2.3'), [('A', False), ('1', ','), ('2', '.'), ('3', False)])
        self.assertEqual(text_cells(',1..'), [(' ', ','), ('1', '.'), (' ', '.')])
        self.assertEqual(text_cells('é'), [('?', False)])

    def test_fourteen_strokes_and_reference_glyphs(self):
        self.assertEqual(len(SEGMENTS), 14)
        self.assertEqual(GLYPHS['0'], 'abcdefij')
        self.assertEqual(GLYPHS['E'], 'adefg')
        self.assertEqual(GLYPHS['F'], 'aefg')
        self.assertEqual(GLYPHS['V'], 'efij')
        self.assertEqual(GLYPHS[':'], 'adhijk')  # Reference hourglass, not punctuation.
        for strokes in GLYPHS.values():
            self.assertTrue(set(strokes) <= SEGMENTS.keys())

    def test_numeric_formatting_overflow_and_text_mode_cache(self):
        widget = VfdDisplay(); widget.resize(400, 100)
        widget.setCharacterCount(8)
        widget.setDecimalSeparator(','); widget.setValue(-12.345)
        self.assertEqual(widget.text, '-12,345')
        self.assertFalse(widget.overflow)
        widget.setCharacterCount(4)
        widget.setDecimals(0)
        widget.setText('12345'); widget.grab()
        self.assertEqual(widget.displayCells(), text_cells('1234'))
        self.assertIsNotNone(widget._cache)
        widget.setValue(12345)
        self.assertIsNone(widget._cache)
        self.assertTrue(widget.overflow)
        self.assertEqual(widget.displayCells(), [('#', False)]*4)
        widget.grab(); widget.setText('12345')
        self.assertIsNone(widget._cache)
        self.assertEqual(widget.displayCells(), text_cells('1234'))
        widget.setCharacterCount(8); widget.setRightAligned(True); widget.setText('12')
        self.assertEqual(widget.displayCells()[-2:], text_cells('12'))
        self.assertEqual(widget.displayCells()[:6], [(' ', False)]*6)

    def test_properties_validate_and_roundtrip(self):
        widget = VfdDisplay()
        self.assertTrue(widget.setProperty('decimalSeparator', ','))
        widget.setProperty('value', 42.5)
        self.assertEqual(widget.text, '42,500')
        self.assertTrue(widget.setProperty('foregroundColor', QColor('#ffba5d')))
        self.assertEqual(widget.foregroundColor.name(), '#ffba5d')
        widget.setCharacterCount(0); self.assertEqual(widget.characterCount, 1)
        widget.setCharacterCount(999); self.assertEqual(widget.characterCount, 64)
        widget.setBrightness(-1); self.assertEqual(widget.brightness, 0)
        widget.setBrightness(101); self.assertEqual(widget.brightness, 100)
        with self.assertRaises(ValueError): widget.setValue(float('nan'))
        with self.assertRaises(ValueError): widget.setDecimalSeparator(';')
        with self.assertRaises(ValueError): widget.setForegroundColor('not-a-color')
        self.assertGreaterEqual(widget.metaObject().indexOfSlot('setValue(double)'), 0)

    def test_paint_cache_resize_brightness_and_disconnection(self):
        widget = VfdDisplay(); widget.resize(720, 96); widget.setText('123,456')
        lit = widget.grab().toImage(); cached = widget._cache
        widget.grab(); self.assertIs(widget._cache, cached)
        widget.setBrightness(0)
        self.assertIsNone(widget._cache)
        self.assertNotEqual(lit, widget.grab().toImage())
        widget.resize(900, 100)
        self.assertEqual(widget.grab().size().width(), round(900*widget.devicePixelRatioF()))
        widget.setConnected(False)
        self.assertEqual(widget.displayCells()[:7], text_cells('NO DATA'))
        self.assertEqual(widget.accessibleDescription(), 'No data')

    def test_glow_spreads_light_and_extinguishes_at_zero_brightness(self):
        widget = VfdDisplay(); widget.resize(400, 120); widget.setCharacterCount(4)
        widget.setText('11'); widget.setGlow(False)
        flat = widget.grab().toImage()
        widget.setGlow(True)
        glowing = widget.grab().toImage()
        self.assertNotEqual(flat, glowing)
        background = widget.backgroundColor.rgb()
        spread = 0
        for y in range(flat.height()):
            for x in range(flat.width()):
                if flat.pixelColor(x, y).rgb() == background:
                    before, after = flat.pixelColor(x, y), glowing.pixelColor(x, y)
                    if after.red()+after.green()+after.blue() > before.red()+before.green()+before.blue():
                        spread += 1
        self.assertGreater(spread, 50)
        widget.setGlowStrength(0)
        self.assertEqual(flat, widget.grab().toImage())
        widget.setGlowStrength(70); widget.setBrightness(0)
        dark_glow = widget.grab().toImage()
        widget.setGlow(False)
        self.assertEqual(dark_glow, widget.grab().toImage())

    def test_glow_properties_invalidate_cache_and_validate_radius(self):
        widget = VfdDisplay(); widget.resize(400, 100); widget.grab()
        self.assertIsNotNone(widget._cache)
        self.assertTrue(widget.setProperty('glowRadius', 9.0))
        self.assertEqual(widget.glowRadius, 9.0)
        self.assertIsNone(widget._cache)
        widget.grab(); widget.setGlowStrength(50)
        self.assertIsNone(widget._cache)
        widget.setGlowRadius(99); self.assertEqual(widget.glowRadius, 24.0)
        widget.setGlowRadius(-1); self.assertEqual(widget.glowRadius, 0.0)
        widget.setGlowStrength(999); self.assertEqual(widget.glowStrength, 100)
        with self.assertRaises(ValueError): widget.setGlowRadius(float('nan'))

    def test_designer_loads_all_vfd_properties(self):
        try:
            from PySide6.QtUiTools import QUiLoader
        except ImportError:
            self.skipTest('PC-only QtUiTools required')
        loader = QUiLoader(); loader.registerCustomWidget(VfdDisplay)
        window = loader.load(str(ROOT/'templates/vfd-1024x600.ui'))
        self.assertIsNotNone(window, loader.errorString())
        displays = window.findChildren(VfdDisplay)
        self.assertEqual(len(displays), 4)
        numeric = window.findChild(VfdDisplay, 'numericVfd')
        self.assertEqual(numeric.characterCount, 8)
        self.assertEqual(numeric.decimalSeparator, ',')
        self.assertEqual(numeric.text, '-12,345')
        self.assertEqual(window.findChild(VfdDisplay, 'amberVfd').foregroundColor.name(), '#ffba5d')
        window.deleteLater()

    def test_generated_vfd_bundle_runs_without_simulator_or_designer(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); bundle = directory/'bundle'
            result = subprocess.run([sys.executable, str(ROOT/'ninjaui_tools.py'), 'build', str(ROOT/'templates/vfd-1024x600.ui'), '--output', str(bundle)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            screenshot = directory/'vfd.png'
            result = subprocess.run([sys.executable, str(bundle/'app.py'), '--quit-after', '400', '--screenshot', str(screenshot)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            image = QImage(str(screenshot))
            self.assertEqual((image.width(), image.height()), (1024, 600))
            self.assertTrue((bundle/'ninjaui/vfd.py').exists())

    def test_optional_hal_reader_marks_failed_vfd_values_unavailable(self):
        window = QWidget(); layout = QVBoxLayout(window)
        widget = VfdDisplay(); widget.setHalPin('position'); layout.addWidget(widget)
        class FakeHAL:
            value = 12.345
            def get_value(self, pin):
                return self.value
        api = FakeHAL(); reader = HalReader(api, window, lambda message: None)
        reader.timer.stop()
        self.assertTrue(widget.connected)
        self.assertEqual(widget.text, '12.345')
        api.value = float('nan'); reader.poll()
        self.assertFalse(widget.connected)
        self.assertEqual(widget.displayCells()[:7], text_cells('NO DATA'))


if __name__ == '__main__':
    unittest.main()
