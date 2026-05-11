"""
ui/page_report_viewer.py
────────────────────────
Report viewer page.

Shows the generated PDF inline using Qt's WebEngineView (if available)
or falls back to rendering each page as a QPixmap via pdf2image / PyMuPDF.
If neither is available, shows a download-path banner with an "Open" button
that launches the system PDF viewer.
"""

import os
import subprocess
import sys

from PyQt5.QtCore    import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QSizePolicy,
)

from utils.constants import C_NAVY, C_GOLD, C_BG, C_WHITE, C_BORDER, C_TEXT_MID, C_GREEN
from utils.widgets   import make_btn_primary, make_btn_secondary

# Try to import a PDF rendering backend (best → fallback)
_BACKEND = None
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    _BACKEND = 'webengine'
except ImportError:
    pass

if _BACKEND is None:
    try:
        import fitz   # PyMuPDF
        _BACKEND = 'pymupdf'
    except ImportError:
        pass

if _BACKEND is None:
    try:
        from pdf2image import convert_from_path
        _BACKEND = 'pdf2image'
    except ImportError:
        pass


class ReportViewerPage(QWidget):
    """
    Displays a generated PDF report.

    Signals:
        back_to_history() — user taps "Back to History"
        new_scan()        — user taps "New Scan"
    """
    back_to_history = pyqtSignal()
    new_scan        = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdf_path = ''
        self.setStyleSheet(f'background:{C_BG};')

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Report area ───────────────────────────────────────────────────────
        self._view_area = QWidget()
        self._view_area.setStyleSheet(f'background:{C_BG};')
        self._view_l = QVBoxLayout(self._view_area)
        self._view_l.setContentsMargins(0, 0, 0, 0)
        self._view_l.setSpacing(0)
        root.addWidget(self._view_area, stretch=1)

        # ── Bottom action bar ─────────────────────────────────────────────────
        bar = QWidget(); bar.setObjectName('rvBar')
        bar.setFixedHeight(72)
        bar.setStyleSheet(
            f'QWidget#rvBar{{background:{C_WHITE};border-top:1px solid {C_BORDER};}}'
            'QWidget#rvBar QLabel{border:none;background:transparent;}'
        )
        bl = QHBoxLayout(bar); bl.setContentsMargins(24, 12, 24, 12); bl.setSpacing(12)

        self._open_btn  = make_btn_secondary('↗  Open in System Viewer')
        self._open_btn.clicked.connect(self._open_external)

        hist_btn = make_btn_secondary('🕒  Back to History')
        hist_btn.clicked.connect(self.back_to_history.emit)

        new_btn  = make_btn_primary('＋  New Scan')
        new_btn.clicked.connect(self.new_scan.emit)

        bl.addWidget(self._open_btn)
        bl.addStretch()
        bl.addWidget(hist_btn)
        bl.addWidget(new_btn)
        root.addWidget(bar)

    # ── Public API ────────────────────────────────────────────────────────────

    def load_report(self, scan: dict, pdf_path: str):
        self._pdf_path = pdf_path
        self._clear_view()

        if not os.path.exists(pdf_path):
            self._show_error(f'File not found:\n{pdf_path}')
            return

        if _BACKEND == 'webengine':
            self._load_webengine(pdf_path)
        elif _BACKEND == 'pymupdf':
            self._load_pymupdf(pdf_path)
        elif _BACKEND == 'pdf2image':
            self._load_pdf2image(pdf_path)
        else:
            self._show_fallback(scan, pdf_path)

    # ── Rendering backends ────────────────────────────────────────────────────

    def _load_webengine(self, path: str):
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtCore import QUrl
        view = QWebEngineView()
        view.setUrl(QUrl.fromLocalFile(path))
        self._view_l.addWidget(view)

    def _load_pymupdf(self, path: str):
        import fitz
        from PyQt5.QtGui import QPixmap, QImage
        doc = fitz.open(path)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f'background:{C_BG};')
        inner = QWidget(); inner.setStyleSheet(f'background:{C_BG};')
        il = QVBoxLayout(inner); il.setContentsMargins(24, 16, 24, 16); il.setSpacing(12)
        for page in doc:
            mat  = fitz.Matrix(2.0, 2.0)
            pix  = page.get_pixmap(matrix=mat)
            img  = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            pm   = QPixmap.fromImage(img)
            lbl  = QLabel()
            lbl.setPixmap(pm)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet('background:#fff;border-radius:4px;border:1px solid #E5E7EB;')
            il.addWidget(lbl)
        il.addStretch()
        scroll.setWidget(inner)
        self._view_l.addWidget(scroll)

    def _load_pdf2image(self, path: str):
        from pdf2image import convert_from_path
        from PyQt5.QtGui import QPixmap, QImage
        pages = convert_from_path(path, dpi=150)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f'background:{C_BG};')
        inner = QWidget(); inner.setStyleSheet(f'background:{C_BG};')
        il = QVBoxLayout(inner); il.setContentsMargins(24, 16, 24, 16); il.setSpacing(12)
        for pil_img in pages:
            data  = pil_img.tobytes('raw', 'RGB')
            img   = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGB888)
            pm    = QPixmap.fromImage(img)
            lbl   = QLabel()
            lbl.setPixmap(pm.scaledToWidth(min(800, pm.width()), Qt.SmoothTransformation))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet('background:#fff;border-radius:4px;border:1px solid #E5E7EB;')
            il.addWidget(lbl)
        il.addStretch()
        scroll.setWidget(inner)
        self._view_l.addWidget(scroll)

    def _show_fallback(self, scan: dict, path: str):
        """No PDF rendering library available — show path and open button."""
        w = QWidget(); w.setStyleSheet(f'background:{C_BG};')
        lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignCenter); lay.setSpacing(16)

        ic = QLabel('📄'); ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet('font-size:52px;border:none;background:transparent;')
        lay.addWidget(ic)

        t = QLabel('Report Generated Successfully')
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(f'color:{C_NAVY};font-size:20px;font-weight:800;border:none;background:transparent;')
        lay.addWidget(t)

        rid = QLabel(f"Report ID: {scan.get('report_id','—')}  ·  Sample: {scan.get('sample_id','—')}")
        rid.setAlignment(Qt.AlignCenter)
        rid.setStyleSheet(f'color:{C_TEXT_MID};font-size:13px;border:none;background:transparent;')
        lay.addWidget(rid)

        # File path pill
        pill = QLabel(path)
        pill.setAlignment(Qt.AlignCenter)
        pill.setWordWrap(True)
        pill.setStyleSheet(
            f'background:{C_WHITE};border-radius:8px;border:1px solid {C_BORDER};'
            f'color:{C_TEXT_MID};font-size:11px;padding:10px 16px;'
        )
        lay.addWidget(pill)

        tip = QLabel('Install PyMuPDF for inline preview:  pip install pymupdf')
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet(
            f'background:{C_GOLD}18;color:{C_NAVY};font-size:11px;'
            'border-radius:6px;border:1px dashed #E8A838;padding:6px 14px;'
        )
        lay.addWidget(tip, alignment=Qt.AlignCenter)

        self._view_l.addWidget(w)

    def _show_error(self, msg: str):
        lbl = QLabel(msg)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f'color:#EF4444;font-size:13px;border:none;background:transparent;')
        self._view_l.addWidget(lbl, alignment=Qt.AlignCenter)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _clear_view(self):
        while self._view_l.count():
            item = self._view_l.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _open_external(self):
        if not self._pdf_path or not os.path.exists(self._pdf_path):
            return
        if sys.platform == 'darwin':
            subprocess.Popen(['open', self._pdf_path])
        elif sys.platform == 'win32':
            os.startfile(self._pdf_path)
        else:
            subprocess.Popen(['xdg-open', self._pdf_path])
