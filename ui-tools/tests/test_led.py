# SPDX-License-Identifier: MIT
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from ninjaui.widgets import LedButton, LedLabel
from ninjaui.hal_reader import HalReader
from ninjaui.profile import check

APP = QApplication.instance() or QApplication([])


class LedTests(unittest.TestCase):
    def test_toggle_and_independent_feedback(self):
        button = LedButton(); button.resize(400, 108); button.show()
        self.addCleanup(button.close)
        clicked = QSignalSpy(button.clicked)
        self.assertFalse(button.active)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.assertTrue(button.isChecked()); self.assertTrue(button.active)
        self.assertEqual(clicked.count(), 1)
        button.setFollowButton(False); button.setActive(True)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.assertFalse(button.isChecked()); self.assertTrue(button.active)
        button.setConnected(False)
        self.assertFalse(button.connected)
        self.assertGreaterEqual(button.metaObject().indexOfSignal('longPressed()'), 0)
        self.assertTrue(button._lamp.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))

    def test_momentary_led_tracks_press_release(self):
        button = LedButton(); button.setCheckable(False); button.show()
        self.addCleanup(button.close)
        QTest.mousePress(button, Qt.MouseButton.LeftButton)
        self.assertTrue(button.active)
        QTest.mouseRelease(button, Qt.MouseButton.LeftButton)
        self.assertFalse(button.active)
        QTest.mousePress(button, Qt.MouseButton.LeftButton)
        button.setEnabled(False)
        self.assertFalse(button.active)
        QTest.mouseRelease(button, Qt.MouseButton.LeftButton)
        button.setEnabled(True)
        button.setFollowButton(False); button.setActive(True)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.assertTrue(button.active)

    def test_label_unicode_properties_and_geometry(self):
        label = LedLabel(); label.setText('Hűtővíz ▶ ■ ⚠'); label.setMinimumHeight(108)
        label.resize(480, 120); label.show(); APP.processEvents()
        self.addCleanup(label.close)
        self.assertEqual(label.text(), 'Hűtővíz ▶ ■ ⚠')
        for name, value in [('active', True), ('ledColor', QColor('#41b1ff')), ('ledOnRight', False), ('glowRadius', 6.0), ('ledDiameter', 24)]:
            self.assertTrue(label.setProperty(name, value))
        self.assertTrue(label.active); self.assertEqual(label.ledColor.name(), '#41b1ff')
        self.assertEqual(label._lamp.x(), 10)
        self.assertGreaterEqual(label.contentsMargins().left(), label._lamp.extent())
        self.assertEqual(label.minimumHeight(), 108)
        self.assertGreaterEqual(label.metaObject().indexOfSlot('setActive(bool)'), 0)
        with self.assertRaises(ValueError): label.setLedColor('not a color')
        with self.assertRaises(ValueError): label.setGlowRadius(float('nan'))

    def test_lamp_glow_is_cached_and_obeys_brightness(self):
        label = LedLabel(); label.resize(400, 100); label.show(); APP.processEvents()
        self.addCleanup(label.close)
        lamp = label._lamp
        off = lamp.grab().toImage()
        label.setActive(True); active = lamp.grab().toImage()
        self.assertNotEqual(off, active)
        cached = lamp._cache; lamp.grab(); self.assertIs(lamp._cache, cached)
        label.setBrightness(0); self.assertIsNone(lamp._cache)
        self.assertEqual(off, lamp.grab().toImage())
        label.setBrightness(100); label.setGlowStrength(0)
        no_glow = lamp.grab().toImage()
        label.setGlow(False); label.setGlowStrength(100)
        self.assertEqual(no_glow, lamp.grab().toImage())
        label.setConnected(False)
        self.assertNotEqual(off, lamp.grab().toImage())

    def test_hal_feedback_cannot_follow_button_or_write_outputs(self):
        window = QWidget(); layout = QVBoxLayout(window)
        button, label = LedButton(), LedLabel()
        button.setHalPin('ready'); label.setHalPin('ready')
        layout.addWidget(button); layout.addWidget(label)
        class FakeHAL:
            values = {'ready': True}
            def get_value(self, pin): return self.values[pin]
        api = FakeHAL(); reader = HalReader(api, window, lambda message: None)
        reader.timer.stop()
        self.assertFalse(button.followButton)
        self.assertTrue(button.active); self.assertTrue(label.active)
        button.click(); self.assertTrue(button.active)
        api.values['ready'] = False; reader.poll()
        self.assertTrue(button.isChecked()); self.assertFalse(button.active)
        api.values.clear(); reader.poll()
        self.assertFalse(button.connected); self.assertFalse(label.connected)

    def test_new_led_bundle_has_icon_unicode_and_no_source_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); source = directory/'work/panel.ui'; bundle = directory/'bundle'
            result = subprocess.run([sys.executable, str(ROOT/'ninjaui_tools.py'), 'new', '--led', str(source)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((source.parent/'assets/power.png').is_file())
            check(source)
            # Designer may record the registered Python parent of LedButton.
            form = source.read_text().replace('<class>LedButton</class><extends>QPushButton</extends>', '<class>LedButton</class><extends>TouchButton</extends>')
            form = form.replace('<customwidgets>', '<customwidgets><customwidget><class>TouchButton</class><extends>QPushButton</extends><header>ninjaui.widgets</header></customwidget>')
            source.write_text(form)
            check(source)
            result = subprocess.run([sys.executable, str(ROOT/'ninjaui_tools.py'), 'build', str(source), '--output', str(bundle)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            shutil.rmtree(source.parent)
            code = '''import sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtCore import Qt
import compiled_ui
app=QApplication([]); window=QWidget(); ui=compiled_ui.Ui_NinjaLedPanel(); ui.setupUi(window)
assert not ui.iconButton.icon().isNull()
assert ui.startButton.text() == '▶ Start / Unicode'
assert ui.coolantLabel.text() == 'Hűtővíz / Coolant'
assert ui.startButton.active
assert ui.feedbackButton.active and not ui.feedbackButton.followButton
assert not ui.offlineLabel.connected
window.show(); app.processEvents(); assert window.grab().save(sys.argv[2])
'''
            image = directory/'panel.png'
            result = subprocess.run([sys.executable, '-c', code, str(bundle), str(image)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            screen = QImage(str(image))
            self.assertEqual((screen.width(), screen.height()), (1024, 600))

    def test_new_does_not_overwrite_shared_assets_or_leave_partial_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); (directory/'led_icons.qrc').write_text('existing')
            result = subprocess.run([sys.executable, str(ROOT/'ninjaui_tools.py'), 'new', '--led', str(directory/'panel.ui')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((directory/'led_icons.qrc').read_text(), 'existing')
            self.assertFalse((directory/'panel.ui').exists())

    def test_theme_only_icon_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'panel.ui'
            source = (ROOT/'templates/blank-1024x600.ui').read_text().replace('<property name="windowTitle">', '<property name="windowIcon"><iconset theme="media-playback-start"/></property><property name="windowTitle">')
            path.write_text(source)
            with self.assertRaisesRegex(ValueError, 'Theme-only'):
                check(path)

    def test_explicit_font_check_catches_missing_symbol(self):
        font = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        if not font.exists(): self.skipTest('Test fixture font unavailable')
        for text, expected in [('▶■⚠', 0), ('\U0010FFFF', 1)]:
            result = subprocess.run([sys.executable, str(ROOT/'ninjaui_tools.py'), 'font-check', text, '--font-file', str(font)], capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertIn('MISSING' if expected else 'OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
