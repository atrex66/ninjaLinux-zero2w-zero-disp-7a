# SPDX-License-Identifier: MIT
"""Bundle runner: offline preview by default; explicit optional read-only HAL."""
import argparse
import importlib
import json
import math
import os
from pathlib import Path
import sys
from PySide6.QtCore import QTimer, qVersion
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QLabel, QStackedWidget
from .widgets import AxisDisplay, NumericPad, StatusLed, TouchButton


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--demo', action='store_true', help='Synthetic display values; never connects to HAL')
    mode.add_argument('--hal-read', action='store_true', help='Read a private HAL already owned by this user')
    parser.add_argument('--fullscreen', action='store_true')
    parser.add_argument('--screenshot', type=Path)
    parser.add_argument('--quit-after', type=int, default=0, metavar='MS')
    args = parser.parse_args()
    directory = Path(sys.argv[0]).resolve().parent
    manifest = json.loads((directory/'manifest.json').read_text())
    os.chdir(directory)
    app = QApplication([sys.argv[0]])
    app.setStyle('Fusion')
    app.setFont(QFont('DejaVu Sans', 18))
    window = QMainWindow() if manifest['window_class'] == 'QMainWindow' else QWidget()
    ui = getattr(importlib.import_module('compiled_ui'), manifest['form_class'])()
    ui.setupUi(window)
    status = window.findChild(QLabel, 'statusLabel')

    def report(text):
        if status:
            status.setText(text)

    report('DEMO · synthetic values' if args.demo else 'OFFLINE · no HAL connection')
    pages = window.findChild(QStackedWidget, 'pages')
    keypad = window.findChild(NumericPad, 'keypad')
    edit = window.findChild(TouchButton, 'editButton')
    axes = window.findChildren(AxisDisplay)
    leds = window.findChildren(StatusLed)
    # Optional sample wiring; unrelated forms need not use these object names.
    if pages and keypad and edit and axes:
        def show_editor():
            keypad.setValue(axes[0].value)
            pages.setCurrentWidget(keypad.parentWidget())
        def accept(value):
            axes[0].setValue(value)
            pages.setCurrentIndex(0)
        edit.clicked.connect(show_editor)
        keypad.accepted.connect(accept)
        keypad.cancelled.connect(lambda: pages.setCurrentIndex(0))
        edit.setEnabled(not args.hal_read)
    timer = QTimer(window)
    if args.demo:
        phase = [0.0]
        def animate():
            phase[0] += .05
            for index, axis in enumerate(axes):
                axis.setValue(125*math.sin(phase[0]+index))
            for led in leds:
                led.setActive(int(phase[0]) % 2 == 0)
        timer.timeout.connect(animate)
        timer.start(100)
    reader = None
    if args.hal_read:
        from .hal_reader import HalReader, existing_hal_api
        try:
            reader = HalReader(existing_hal_api(), window, report, window)
        except (OSError, RuntimeError, ImportError) as error:
            print(f'HAL: {error}', file=sys.stderr)
            return 1
    window.resize(*manifest['screen'])
    window.showFullScreen() if args.fullscreen else window.show()
    exit_code = [0]
    if args.screenshot:
        def screenshot():
            if not window.grab().save(str(args.screenshot)):
                print('Cannot save screenshot', file=sys.stderr)
                exit_code[0] = 1
                app.quit()
        QTimer.singleShot(200, screenshot)
    if args.quit_after > 0:
        QTimer.singleShot(max(300 if args.screenshot else 1, args.quit_after), app.quit)
    print(f'ninjaUI ready: {window.width()}x{window.height()}, Qt {qVersion()}', flush=True)
    result = app.exec()
    return exit_code[0] or result
