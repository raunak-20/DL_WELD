"""
utils/widgets.py
────────────────
Reusable styled widgets and factory functions shared across all UI pages.
Add new shared components here rather than inside individual page files.
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui  import QColor, QPen, QBrush, QFont, QPixmap, QPainter
from PyQt5.QtWidgets import (
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, QFrame, QWidget
)

from utils.constants import (
    C_NAVY, C_NAVY_DARK, C_NAVY_MID, C_GOLD, C_GOLD_DRK,
    C_BG, C_WHITE, C_BORDER, C_TEXT_MID, C_TEXT_LITE
)


# ─── Labels ───────────────────────────────────────────────────────────────────

class FieldLabel(QLabel):
    """Bold field label above an input widget."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f'QLabel {{ color: {C_NAVY}; font-size: 13px; font-weight: 600; '
            'border: none; background: transparent; }}'
        )


class SectionLabel(QLabel):
    """Small all-caps section heading."""
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(
            f'QLabel {{ color: {C_TEXT_MID}; font-size: 10px; font-weight: 700; '
            'letter-spacing: 1.2px; border: none; background: transparent; '
            'margin-top: 6px; margin-bottom: 2px; }}'
        )


class Divider(QFrame):
    """Thin horizontal rule."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setStyleSheet(f'color: {C_BORDER};')
        self.setFixedHeight(1)


class ToastWidget(QLabel):
    """Floating toast notification that auto-dismisses."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.setAlignment(Qt.AlignCenter)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_toast(self, message: str, icon: str = '✓',
                   color: str = C_NAVY, duration: int = 3000):
        self.setText(f'  {icon}  {message}  ')
        self.setStyleSheet(
            f'background: {color}; color: white; padding: 10px 20px; '
            'border-radius: 24px; font-size: 13px; font-weight: 600; '
            'border: 1px solid rgba(255,255,255,0.15);'
        )
        self.adjustSize()
        self.setVisible(True)
        self.raise_()
        self._reposition()
        self._timer.start(duration)

    def _reposition(self):
        if self.parent():
            pw = self.parent().width()
            ph = self.parent().height()
            self.move((pw - self.width()) // 2, ph - self.height() - 20)

    def resizeEvent(self, event):
        self._reposition()
        super().resizeEvent(event)


# ─── Input widgets ────────────────────────────────────────────────────────────

class InputField(QLineEdit):
    """Styled single-line text input."""
    def __init__(self, placeholder: str = '', parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(42)
        self.setStyleSheet(
            f'QLineEdit {{ background: {C_WHITE}; border: 1.5px solid {C_BORDER}; '
            'border-radius: 8px; padding: 9px 12px; font-size: 13px; color: #1B2A4A; }}'
            f'QLineEdit:focus {{ border-color: {C_GOLD}; }}'
            f'QLineEdit:read-only {{ background: #F9FAFB; color: {C_TEXT_MID}; }}'
        )


class ComboField(QComboBox):
    """Styled dropdown combo box."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(42)
        self.setStyleSheet(
            f'QComboBox {{ background: {C_WHITE}; border: 1.5px solid {C_BORDER}; '
            'border-radius: 8px; padding: 9px 12px; font-size: 13px; color: #1B2A4A; }}'
            f'QComboBox:focus {{ border-color: {C_GOLD}; }}'
            'QComboBox::drop-down { border: none; width: 28px; }'
            'QComboBox::down-arrow { image: none; width: 10px; height: 10px; }'
            f'QComboBox QAbstractItemView {{ background: {C_WHITE}; '
            f'border: 1px solid {C_BORDER}; border-radius: 8px; padding: 4px; '
            'selection-background-color: #EFF6FF; }}'
        )


class SpinField(QSpinBox):
    """Styled integer spin box."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(42)
        self.setButtonSymbols(QSpinBox.UpDownArrows)
        self.setStyleSheet(
            f'QSpinBox {{ background: {C_WHITE}; border: 1.5px solid {C_BORDER}; '
            'border-radius: 8px; padding: 9px 12px; font-size: 13px; color: #1B2A4A; }}'
            f'QSpinBox:focus {{ border-color: {C_GOLD}; }}'
        )


# ─── Button factories ─────────────────────────────────────────────────────────

def make_btn_primary(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumHeight(48)
    btn.setStyleSheet(
        f'QPushButton {{ background: {C_GOLD}; color: {C_NAVY_DARK}; border: none; '
        'border-radius: 10px; padding: 12px 20px; font-size: 14px; font-weight: 700; }}'
        f'QPushButton:hover {{ background: {C_GOLD_DRK}; }}'
        'QPushButton:disabled { background: #E5E7EB; color: #9CA3AF; }'
    )
    return btn


def make_btn_secondary(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumHeight(48)
    btn.setStyleSheet(
        f'QPushButton {{ background: {C_WHITE}; color: {C_NAVY}; '
        f'border: 1.5px solid {C_BORDER}; border-radius: 10px; '
        'padding: 12px 20px; font-size: 14px; font-weight: 600; }}'
        f'QPushButton:hover {{ background: #F3F4F6; border-color: #9CA3AF; }}'
    )
    return btn


def make_btn_ghost(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumHeight(40)
    btn.setStyleSheet(
        f'QPushButton {{ background: transparent; color: {C_TEXT_MID}; border: none; '
        'border-radius: 8px; padding: 8px 14px; font-size: 13px; }}'
        'QPushButton:hover { background: #F3F4F6; }'
    )
    return btn
