# SPDX-License-Identifier: MIT
"""Loaded only by PC-side pyside6-designer, never by the target runtime."""
from PySide6.QtDesigner import QPyDesignerCustomWidgetCollection
from ninjaui.widgets import StatusLed, AxisDisplay, TouchButton, NumericPad, VfdDisplay

for cls in (StatusLed, AxisDisplay, TouchButton, NumericPad, VfdDisplay):
    QPyDesignerCustomWidgetCollection.registerCustomWidget(
        cls, module='ninjaui.widgets', group='ninjaLinux',
        tool_tip=cls.__doc__.splitlines()[0], container=False,
        xml=f'<ui language="c++"><widget class="{cls.__name__}" name="{cls.__name__[0].lower()+cls.__name__[1:]}"/></ui>')
