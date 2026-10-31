#!/usr/bin/env python3
"""Minimal ninjaLinux USB cartridge. Uses the system's PySide6/EGLFS."""
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
label = QLabel('ninjaLinux\nUSB cartridge / alkalmazás-cartridge')
label.setAlignment(Qt.AlignmentFlag.AlignCenter)
label.setStyleSheet('background: #102129; color: #6fffd4; font-size: 36px;')
label.resize(1024, 600)
label.showFullScreen()
sys.exit(app.exec())
