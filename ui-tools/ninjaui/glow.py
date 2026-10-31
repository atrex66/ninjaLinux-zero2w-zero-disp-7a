# SPDX-License-Identifier: MIT
"""Native Qt bloom helper shared by the VFD and LED widgets."""
from PySide6.QtCore import Qt


def soften(image, radius):
    """Approximate soft bloom with two native smooth resamples, respecting DPI."""
    divisor = max(1.0, radius*image.devicePixelRatioF())
    small = image.scaled(max(1, round(image.width()/divisor)),
                         max(1, round(image.height()/divisor)),
                         Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    return small.scaled(image.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
