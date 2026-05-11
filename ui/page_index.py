"""
ui/page_index.py
────────────────
Home screen with hero logo, Start New Scan, Scan History, and stats cards.
"""

import os
import datetime

from PyQt5.QtCore    import Qt, pyqtSignal
from PyQt5.QtGui     import QPixmap
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)

from utils.constants import (
    C_NAVY, C_NAVY_DARK, C_GOLD, C_BG, C_WHITE, C_BORDER, C_TEXT_MID,
    LOGO_PRIMARY, load_scans,
)
from utils.widgets import make_btn_primary, make_btn_secondary


class IndexPage(QWidget):
    navigate_new_scan = pyqtSignal()
    navigate_history  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f'background: {C_BG};')

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_hero(), stretch=2)
        root.addWidget(self._build_actions(), stretch=3)

    # ── Hero (dark gradient section) ──────────────────────────────────────────

    def _build_hero(self) -> QWidget:
        hero = QWidget()
        hero.setStyleSheet(
            f'background: qlineargradient(x1:0,y1:0,x2:0,y2:1,'
            f'stop:0 {C_NAVY_DARK}, stop:1 #1B2A4A);'
        )
        lay = QVBoxLayout(hero)
        lay.setContentsMargins(40, 50, 40, 44)
        lay.setSpacing(14)
        lay.setAlignment(Qt.AlignCenter)

        # Logo badge
        # ── To use a SECONDARY logo on the home hero ──────────────────────────
        # Replace  LOGO_PRIMARY  below with  LOGO_SECONDARY  from constants.py.
        # ─────────────────────────────────────────────────────────────────────
        logo = QLabel()
        logo.setFixedSize(110, 110)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            'background: rgba(255,255,255,0.95); border-radius: 24px; '
            'border: 2px solid rgba(232,168,56,0.4);'
        )
        if os.path.exists(LOGO_PRIMARY):
            pm = QPixmap(LOGO_PRIMARY).scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pm)
        lay.addWidget(logo, alignment=Qt.AlignCenter)

        title = QLabel('Weld Defect Inspector')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            'color: #FFFFFF; font-size: 26px; font-weight: 800; '
            'letter-spacing: -0.5px; border: none; background: transparent;'
        )
        lay.addWidget(title)

        sub = QLabel('AI-powered weld quality analysis & reporting')
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(
            'color: rgba(255,255,255,0.65); font-size: 14px; border: none; background: transparent;'
        )
        lay.addWidget(sub)

        divider = QLabel()
        divider.setFixedSize(60, 3)
        divider.setStyleSheet(f'background: {C_GOLD}; border-radius: 2px; border: none;')
        lay.addWidget(divider, alignment=Qt.AlignCenter)

        return hero

    # ── Action area ───────────────────────────────────────────────────────────

    def _build_actions(self) -> QWidget:
        area = QWidget()
        area.setStyleSheet(f'background: {C_BG};')
        lay = QVBoxLayout(area)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(14)

        scan_btn = make_btn_primary('▶   Start New Scan')
        scan_btn.setMinimumHeight(56)
        scan_btn.setStyleSheet(
            scan_btn.styleSheet()
            + f'QPushButton {{ font-size: 16px; background: {C_GOLD}; }}'
        )
        scan_btn.clicked.connect(self.navigate_new_scan.emit)

        hist_btn = make_btn_secondary('🕒   Scan History')
        hist_btn.setMinimumHeight(52)
        hist_btn.clicked.connect(self.navigate_history.emit)

        lay.addWidget(scan_btn)
        lay.addWidget(hist_btn)
        lay.addLayout(self._build_stats())
        lay.addStretch()

        return area

    def _build_stats(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        today_str = datetime.datetime.now().strftime('%d %b %Y')

        def _total():
            return str(len(load_scans()))

        def _today():
            return str(sum(
                1 for s in load_scans()
                if s.get('scan_date', '').startswith(today_str)
            ))

        for label, getter in [('Total Scans', _total), ('Today', _today), ('Location', lambda: 'Bay 3, Plant A')]:
            card = QFrame()
            card.setObjectName('statCard')
            card.setStyleSheet(
                f'QFrame#statCard {{ background: {C_WHITE}; border-radius: 10px; '
                f'border: 1px solid {C_BORDER}; }}'
                'QFrame#statCard QLabel { border: none; background: transparent; }'
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 10, 14, 10)
            cl.setSpacing(2)

            val = QLabel(getter())
            val.setAlignment(Qt.AlignCenter)
            val.setStyleSheet(f'color: {C_NAVY}; font-size: 18px; font-weight: 800;')

            key = QLabel(label)
            key.setAlignment(Qt.AlignCenter)
            key.setStyleSheet(f'color: {C_TEXT_MID}; font-size: 11px;')

            cl.addWidget(val)
            cl.addWidget(key)
            row.addWidget(card)

        return row
