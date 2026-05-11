"""
ui/topbar.py
────────────
The persistent top bar rendered above every page.
Contains: back button, logo, gold accent, title/subtitle, status dot.
"""

import os

from PyQt5.QtCore    import Qt, pyqtSignal
from PyQt5.QtGui     import QPixmap
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton

from utils.constants import (
    C_NAVY, C_BG, C_BORDER, C_WHITE, C_GOLD, C_TEXT_MID, C_GREEN,
    LOGO_PRIMARY,
)


class TopBar(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('topbar')
        self.setFixedHeight(60)
        self.setStyleSheet(
            '#topbar { background: #FFFFFF; border-bottom: 1px solid #E5E7EB; }'
            '#topbar QLabel { border: none; background: transparent; }'
        )

        h = QHBoxLayout(self)
        h.setContentsMargins(16, 0, 16, 0)
        h.setSpacing(12)

        # ── Back button ───────────────────────────────────────────────────────
        self.back_btn = QPushButton('← Back')
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setFixedHeight(36)
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.back_btn.setStyleSheet(
            f'QPushButton {{ background: {C_BG}; color: {C_NAVY}; '
            f'border: 1.5px solid {C_BORDER}; border-radius: 8px; '
            'padding: 6px 14px; font-size: 13px; font-weight: 600; }}'
            'QPushButton:hover { background: #E5E7EB; }'
        )
        h.addWidget(self.back_btn)

        # ── Logo ──────────────────────────────────────────────────────────────
        # To show a different logo in the topbar, change LOGO_PRIMARY in
        # utils/constants.py  or pass logo_path to this constructor.
        logo = QLabel()
        logo.setFixedSize(38, 38)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            f'background: {C_WHITE}; border-radius: 8px; border: 1.5px solid {C_BORDER};'
        )
        if os.path.exists(LOGO_PRIMARY):
            pm = QPixmap(LOGO_PRIMARY).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pm)
        h.addWidget(logo)

        # ── Gold accent bar ────────────────────────────────────────────────────
        accent = QLabel()
        accent.setFixedSize(3, 32)
        accent.setStyleSheet(f'background: {C_GOLD}; border-radius: 2px; border: none;')
        h.addWidget(accent)

        # ── Title / subtitle ──────────────────────────────────────────────────
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        self._title = QLabel('Weld Inspector')
        self._title.setStyleSheet(
            f'color: {C_NAVY}; font-size: 16px; font-weight: 700; '
            'border: none; background: transparent;'
        )
        self._sub = QLabel('AI-Powered Visual Inspection System')
        self._sub.setStyleSheet(
            f'color: {C_TEXT_MID}; font-size: 11px; border: none; background: transparent;'
        )
        title_col.addWidget(self._title)
        title_col.addWidget(self._sub)
        h.addLayout(title_col)
        h.addStretch()

        # ── Status indicator ──────────────────────────────────────────────────
        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        self._dot.setStyleSheet(f'background: {C_GREEN}; border-radius: 4px; border: none;')
        self._status = QLabel('System Ready')
        self._status.setStyleSheet(
            f'color: {C_TEXT_MID}; font-size: 11px; border: none; background: transparent;'
        )
        h.addWidget(self._dot)
        h.addWidget(self._status)

    # ── Public setters ────────────────────────────────────────────────────────

    def set_back_visible(self, visible: bool):
        self.back_btn.setVisible(visible)

    def set_title(self, title: str, subtitle: str = ''):
        self._title.setText(title)
        self._sub.setText(subtitle or 'AI-Powered Visual Inspection System')

    def set_status(self, text: str, color: str = C_GREEN):
        self._status.setText(text)
        self._dot.setStyleSheet(f'background: {color}; border-radius: 4px; border: none;')
