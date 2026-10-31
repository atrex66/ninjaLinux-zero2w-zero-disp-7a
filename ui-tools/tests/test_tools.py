# SPDX-License-Identifier: MIT
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ninjaui.profile import check, PROFILE
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from ninjaui.widgets import AxisDisplay, NumericPad, StatusLed, TouchButton, VfdDisplay, LedButton, LedLabel
from ninjaui.hal_reader import HalReader, existing_hal_api

APP = QApplication.instance() or QApplication([])


class ToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def form(self, source):
        path = self.directory/'test.ui'
        path.write_text(source)
        return path

    def test_templates_and_target_module_profile(self):
        for path in (ROOT/'templates').glob('*.ui'):
            check(path)
        package = (ROOT.parent/'package/python-pyside6/python-pyside6.mk').read_text()
        self.assertIn('-DMODULES="'+';'.join(m[2:] for m in PROFILE['modules'])+'"', package)
        self.assertIn('VERSION = '+PROFILE['target_pyside'], package)

    def test_rejects_unsupported_widgets_and_custom_imports(self):
        template = (ROOT/'templates/panel-1024x600.ui').read_text()
        for source, error in [(template.replace('class="QLabel"', 'class="QWebEngineView"', 1), 'Unsupported widget'),
                              (template.replace('<header>ninjaui.widgets</header>', '<header>external.module</header>', 1), 'profile base class')]:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                check(self.form(source))

    def test_rejects_wrong_geometry_duplicate_names_and_xml_entities(self):
        template = (ROOT/'templates/blank-1024x600.ui').read_text()
        for source in [template.replace('<width>1024</width>', '<width>800</width>', 1),
                       template.replace('name="statusLabel"', 'name="titleLabel"'),
                       '<!DOCTYPE ui>'+template]:
            with self.assertRaises(ValueError):
                check(self.form(source))

    def test_resources_reject_escape_and_external_stylesheet(self):
        template = (ROOT/'templates/blank-1024x600.ui').read_text()
        for path in ['../outside.qrc', 'missing.qrc']:
            with self.assertRaises(ValueError):
                check(self.form(template.replace('<resources/>', f'<resources><include location="{path}"/></resources>')))
        with self.assertRaisesRegex(ValueError, 'Stylesheet'):
            check(self.form(template.replace('QWidget {', 'QWidget { image: url(/tmp/example.png);', 1)))

    def test_build_bundle_runs_after_ui_and_png_sources_are_removed(self):
        image = self.directory/'icon.png'
        self.assertTrue(APP.primaryScreen() is not None)
        from PySide6.QtGui import QImage, QColor
        picture = QImage(4, 4, QImage.Format.Format_ARGB32)
        picture.fill(QColor('red'))
        self.assertTrue(picture.save(str(image)))
        (self.directory/'icons.qrc').write_text('<RCC><qresource prefix="/"><file>icon.png</file></qresource></RCC>')
        template = (ROOT/'templates/panel-1024x600.ui').read_text().replace('<resources/>', '<resources><include location="icons.qrc"/></resources>')
        template = template.replace('QWidget {', 'QWidget { image: url(:/icon.png);', 1)
        form = self.form(template)
        bundle = self.directory/'bundle'
        command = [sys.executable, str(ROOT/'ninjaui_tools.py'), 'build', str(form), '--output', str(bundle)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        refusal = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn('Output already exists', refusal.stderr)
        form.unlink(); image.unlink(); (self.directory/'icons.qrc').unlink()
        env = os.environ.copy()
        env.pop('PYSIDE_DESIGNER_PLUGINS', None)
        screen = self.directory/'screen.png'
        result = subprocess.run([sys.executable, str(bundle/'app.py'), '--screenshot', str(screen), '--quit-after', '350'], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        loaded = QImage(str(screen))
        self.assertEqual((loaded.width(), loaded.height()), (1024, 600))
        self.assertFalse((bundle/'ninjaui/profile.py').exists())
        self.assertTrue((bundle/'app.py').exists())

    def test_designer_registration_and_custom_form_loading(self):
        try:
            from PySide6.QtDesigner import QPyDesignerCustomWidgetCollection
            from PySide6.QtUiTools import QUiLoader
        except ImportError:
            self.skipTest('Full PC-side PySide6 Designer/UiTools required')
        import runpy
        runpy.run_path(str(ROOT/'designer/register_ninjaui.py'))
        registered = {w.name(): w.includeFile() for w in QPyDesignerCustomWidgetCollection.instance().customWidgets()}
        for name in PROFILE['custom_widgets']:
            self.assertEqual(registered[name], 'ninjaui.widgets')
        loader = QUiLoader()
        for cls in (StatusLed, AxisDisplay, TouchButton, NumericPad, VfdDisplay, LedButton, LedLabel):
            loader.registerCustomWidget(cls)
        form = loader.load(str(ROOT/'templates/panel-1024x600.ui'))
        self.assertIsNotNone(form, loader.errorString())
        self.assertIsInstance(form.findChild(AxisDisplay, 'axisA'), AxisDisplay)
        self.assertEqual(form.findChild(AxisDisplay, 'axisA').value, 125.0)
        self.assertGreaterEqual(form.findChild(AxisDisplay, 'axisA').metaObject().indexOfSlot('setValue(double)'), 0)
        form.deleteLater()

    def test_numeric_pad_decimal_sign_backspace_accept_cancel(self):
        pad = NumericPad()
        accepted, cancelled = QSignalSpy(pad.accepted), QSignalSpy(pad.cancelled)
        for key in ('1', '2', '.', '3', '4', '⌫', '±', 'OK'):
            pad.inputKey(key)
        self.assertEqual(accepted.at(0), [-12.3])
        pad.inputKey('Cancel')
        self.assertEqual(cancelled.count(), 1)
        pad.inputKey('C'); pad.inputKey('±'); pad.inputKey('⌫'); pad.inputKey('OK')
        self.assertEqual(accepted.count(), 1)  # A bare '-' is not a number.

    def test_numeric_pad_rejects_nonfinite_values(self):
        pad = NumericPad()
        with self.assertRaises(ValueError):
            pad.setValue(float('inf'))
        axis = AxisDisplay()
        with self.assertRaises(ValueError):
            axis.setValue(float('nan'))

    def test_long_press_one_second_and_disabled_cancellation(self):
        button = TouchButton(); button.show()
        self.addCleanup(button.close)
        held = QSignalSpy(button.longPressed)
        QTest.mousePress(button, Qt.MouseButton.LeftButton)
        QTest.qWait(700)
        self.assertEqual(held.count(), 0)
        QTest.qWait(450)
        self.assertEqual(held.count(), 1)
        QTest.mouseRelease(button, Qt.MouseButton.LeftButton)
        QTest.mousePress(button, Qt.MouseButton.LeftButton)
        button.setEnabled(False)
        QTest.qWait(1100)
        self.assertEqual(held.count(), 1)

    def test_system_hal_is_rejected_before_import(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import stat
        with patch('ninjaui.hal_reader.Path.stat', return_value=SimpleNamespace(st_mode=stat.S_IFSOCK, st_uid=os.getuid())), \
             patch('ninjaui.hal_reader.importlib.util.find_spec', return_value=SimpleNamespace(origin='/usr/lib/python3/dist-packages/hal.py')), \
             patch('ninjaui.hal_reader.importlib.import_module') as load:
            with self.assertRaisesRegex(RuntimeError, 'private ahal'):
                existing_hal_api()
            load.assert_not_called()

    def test_missing_hal_values_are_explicitly_disconnected(self):
        window = QWidget(); layout = QVBoxLayout(window)
        axis, led, unbound = AxisDisplay(), StatusLed(), AxisDisplay()
        axis.halPin, led.halPin = 'position', 'ready'
        for widget in (axis, led, unbound):
            layout.addWidget(widget)
        class FakeHAL:
            values = {'position': 12.5, 'ready': True}
            def get_value(self, pin):
                return self.values[pin]
        fake = FakeHAL(); reports = []
        reader = HalReader(fake, window, reports.append)
        reader.timer.stop()
        self.assertTrue(axis.connected)
        self.assertEqual(axis.value, 12.5)
        self.assertTrue(led.active)
        self.assertFalse(unbound.connected)
        fake.values.clear()
        reader.poll()
        self.assertFalse(axis.connected)
        self.assertFalse(led.connected)
        self.assertIn('—', axis.text())
        self.assertIn('unavailable', reports[-1])


if __name__ == '__main__':
    unittest.main()
