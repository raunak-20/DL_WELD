#!/usr/bin/env python3
"""
main.py
───────
Entry point for the Weld Inspector PyQt5 application.

Run:
    python3 main.py

Requirements:
    pip install pyqt5 opencv-python

Optional (for AI inference on Raspberry Pi / Linux):
    pip install onnxruntime          # CPU
    pip install onnxruntime-gpu      # GPU / CUDA

Project structure:
    main.py                         ← you are here
    controller/
        app_controller.py           ← navigation + data flow
    ui/
        topbar.py                   ← persistent top bar
        page_index.py               ← home screen
        page_new_scan.py            ← 4-step specimen form
        page_camera.py              ← live camera + capture
        page_history.py             ← past scans list
        page_analysis.py            ← ML results (placeholder)
    services/
        camera_service.py           ← OpenCV camera wrapper
        ai_service.py               ← RTMDet / ONNX inference
    utils/
        constants.py                ← palette, paths, storage
        widgets.py                  ← shared Qt widget factories
    static/
        DSES-Logo.png               ← primary logo (topbar + home)
        DSES-Logo-2.png             ← optional secondary logo
    scans/                          ← saved capture images
    scans.json                      ← scan records (auto-created)
"""

import sys
import os

# Make sure imports resolve from the project root regardless of CWD
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# FIX: Import onnxruntime BEFORE PyQt5 to avoid DLL conflicts on Windows!
import onnxruntime

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QStackedWidget
from PyQt5.QtGui     import QFont, QFontDatabase
from PyQt5.QtCore    import Qt

from utils.constants    import C_BG, C_NAVY
from ui.topbar          import TopBar
from utils.widgets      import ToastWidget
from controller         import AppController


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Weld Inspector — AI Visual Inspection')
        self.resize(900, 720)
        self.setMinimumSize(480, 600)
        self.setStyleSheet(f'QMainWindow {{ background: {C_BG}; }}')

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Shared top bar
        self.topbar = TopBar()
        root.addWidget(self.topbar)

        # Page stack — controller populates this
        self.stack = QStackedWidget()
        root.addWidget(self.stack, stretch=1)

        # Controller wires everything together
        self.controller = AppController(self.stack, self.topbar, parent=self)

        # Global toast (sits on top of everything)
        self.toast = ToastWidget(self)

        # Kiosk / full-screen on Linux (Raspberry Pi)
        if sys.platform.startswith('linux'):
            self.showFullScreen()
        else:
            self.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.toast._reposition()

    def closeEvent(self, event):
        self.controller.cleanup()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Weld Inspector')
    app.setOrganizationName('DSES')

    # Load IBM Plex Sans if present (RPi / Ubuntu), fall back silently
    QFontDatabase.addApplicationFont(
        '/usr/share/fonts/truetype/ibm-plex/IBMPlexSans-Regular.ttf'
    )
    app.setFont(QFont('IBM Plex Sans', 11))

    win = MainWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
