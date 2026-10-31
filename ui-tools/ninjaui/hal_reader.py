# SPDX-License-Identifier: MIT
"""Optional existing-runtime reader. No HAL component creation or write API."""
import importlib
import importlib.util
import os
from pathlib import Path
import stat
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QWidget
from .widgets import AxisDisplay, StatusLed


def existing_hal_api():
    path = Path(f'/tmp/automation-hal-{os.getuid()}/control.sock')
    info = path.stat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError('No private HAL session owned by the current user')
    # Use /opt/automation-hal/bin/ahal python to select the private binding.
    spec = importlib.util.find_spec('hal')
    if spec is None or not spec.origin or not Path(spec.origin).resolve().is_relative_to('/opt/automation-hal'):
        raise RuntimeError('Use the private ahal python launcher, not system LinuxCNC')
    return importlib.import_module('hal')


class HalReader(QObject):
    def __init__(self, api, window, report, parent=None):
        super().__init__(parent)
        self.api, self.report = api, report
        widgets = [w for w in window.findChildren(QWidget) if isinstance(w, (AxisDisplay, StatusLed))]
        for widget in widgets:
            widget.setConnected(False)
        self.bindings = [(w, w.halPin) for w in widgets if w.halPin]
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll)
        self.poll()
        self.timer.start()

    def poll(self):
        errors = []
        for widget, pin in self.bindings:
            try:
                value = self.api.get_value(pin)
                if isinstance(widget, StatusLed):
                    if not isinstance(value, (bool, int)):
                        raise ValueError('LED expects a bit/integer pin')
                    widget.setActive(bool(value))
                else:
                    widget.setValue(float(value))
                widget.setConnected(True)
            except (ValueError, RuntimeError, TypeError, KeyError) as error:
                widget.setConnected(False)
                errors.append(f'{pin}: {error}')
        self.report('HAL read-only · '+str(len(self.bindings))+' pins' if not errors else 'HAL unavailable · '+'; '.join(errors))
