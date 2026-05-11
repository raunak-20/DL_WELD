"""
ui/page_history.py
──────────────────
Scan history page.

Changes from previous version:
  • Status badge removed entirely
  • Each card is clickable → emits scan_selected(scan_dict)
    so the controller can navigate to the report viewer
"""

from PyQt5.QtCore    import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QGridLayout, QPushButton,
)

from utils.constants import (
    C_NAVY, C_GOLD, C_BG, C_WHITE, C_BORDER, C_TEXT_MID, C_TEXT_LITE,
    load_scans,
)
from utils.widgets import Divider, make_btn_ghost


class ScanHistoryPage(QWidget):
    scan_selected = pyqtSignal(dict)   # emitted when user taps a card

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f'background:{C_BG};')

        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # Header strip
        hdr = QWidget(); hdr.setObjectName('histHdr'); hdr.setFixedHeight(56)
        hdr.setStyleSheet(
            f'QWidget#histHdr{{background:{C_WHITE};border-bottom:1px solid {C_BORDER};}}'
            'QWidget#histHdr QLabel{border:none;background:transparent;}'
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20,0,20,0)
        self.count_lbl = QLabel()
        self.count_lbl.setStyleSheet(f'color:{C_TEXT_MID};font-size:13px;border:none;background:transparent;')
        refresh = make_btn_ghost('↻  Refresh'); refresh.clicked.connect(self.refresh)
        hl.addWidget(self.count_lbl); hl.addStretch(); hl.addWidget(refresh)
        root.addWidget(hdr)

        # Cards
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(f'background:{C_BG};')
        self.content = QWidget(); self.content.setStyleSheet(f'background:{C_BG};')
        self.content_l = QVBoxLayout(self.content)
        self.content_l.setContentsMargins(20,16,20,16); self.content_l.setSpacing(10)
        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, stretch=1)

        self.refresh()

    def refresh(self):
        while self.content_l.count():
            item = self.content_l.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        scans = load_scans()
        self.count_lbl.setText(f'{len(scans)} scan{"s" if len(scans)!=1 else ""} recorded')

        if not scans:
            self.content_l.addWidget(self._empty_state())
        else:
            for sc in reversed(scans):
                self.content_l.addWidget(self._make_card(sc))
        self.content_l.addStretch()

    def _empty_state(self):
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignCenter); lay.setSpacing(10)
        lay.setContentsMargins(0,60,0,0)
        for text, style in [
            ('🔍', 'font-size:40px;border:none;background:transparent;'),
            ('No scans yet', f'color:{C_TEXT_MID};font-size:16px;font-weight:600;border:none;background:transparent;'),
            ('Start a new scan to see results here.', f'color:{C_TEXT_LITE};font-size:13px;border:none;background:transparent;'),
        ]:
            lbl = QLabel(text); lbl.setAlignment(Qt.AlignCenter); lbl.setStyleSheet(style)
            lay.addWidget(lbl)
        return w

    def _make_card(self, sc: dict) -> QFrame:
        card = QFrame(); card.setObjectName('histCard')
        card.setStyleSheet(
            f'QFrame#histCard{{background:{C_WHITE};border-radius:12px;border:1px solid {C_BORDER};}}'
            f'QFrame#histCard:hover{{border-color:{C_GOLD};background:#FFFDF5;}}'
            'QFrame#histCard QLabel{border:none;background:transparent;}'
        )
        card.setCursor(Qt.PointingHandCursor)
        cl = QVBoxLayout(card); cl.setContentsMargins(18,14,18,16); cl.setSpacing(8)

        # Top row: sample ID + "View Report" link
        top = QHBoxLayout()
        sid = QLabel(sc.get('sample_id') or '—')
        sid.setStyleSheet(f'color:{C_NAVY};font-size:16px;font-weight:800;')
        top.addWidget(sid); top.addStretch()

        view_lbl = QLabel('View Report  →')
        view_lbl.setStyleSheet(
            f'color:{C_GOLD};font-size:12px;font-weight:700;'
            'border:none;background:transparent;'
        )
        top.addWidget(view_lbl)
        cl.addLayout(top)
        cl.addWidget(Divider())

        # Meta grid (2 columns, no status)
        grid = QGridLayout(); grid.setSpacing(6)
        dims = f"{sc.get('width','?')} × {sc.get('height','?')} mm"
        meta = [
            ('Report ID',  sc.get('report_id','—')),
            ('Scan #',     str(sc.get('scan_number','—'))),
            ('Operator',   sc.get('operator','—')),
            ('Date',       sc.get('scan_date','—')),
            ('Specimen',   sc.get('specimen_type','—')),
            ('Material',   sc.get('material','—')),
            ('Dimensions', dims),
            ('Process',    sc.get('welding_process','—')),
        ]
        for i,(key,val) in enumerate(meta):
            row, col = divmod(i, 2)
            pair = QHBoxLayout()
            kl = QLabel(key+':')
            kl.setStyleSheet(f'color:{C_TEXT_MID};font-size:11px;min-width:68px;border:none;background:transparent;')
            vl = QLabel(val)
            vl.setStyleSheet(f'color:{C_NAVY};font-size:12px;font-weight:600;border:none;background:transparent;')
            vl.setWordWrap(True)
            pair.addWidget(kl); pair.addWidget(vl,1)
            grid.addLayout(pair,row,col)
        cl.addLayout(grid)

        # Make the whole card clickable via mousePressEvent override
        card.mousePressEvent = lambda event, s=sc: self.scan_selected.emit(s)
        return card
