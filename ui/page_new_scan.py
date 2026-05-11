"""
ui/page_new_scan.py
───────────────────
4-step wizard for entering specimen details before opening the camera.

Steps:
  0 — Identification  (sample ID, operator, auto-filled report ID / date)
  1 — Specimen Info   (type, joint config, material)
  2 — Dimensions      (width × height as plain text inputs, no thickness)
  3 — Process         (welding process, industry, notes)
"""

from math import gcd

from PyQt5.QtCore    import Qt, QTimer, pyqtSignal
from PyQt5.QtGui     import QPainter, QColor, QPen, QBrush, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QStackedWidget, QScrollArea, QMessageBox
)

from utils.constants import (
    C_NAVY, C_GOLD, C_BG, C_WHITE, C_BORDER, C_TEXT_MID, C_TEXT_LITE,
    gen_report_id, gen_scan_number, now_str,
)
from utils.widgets import (
    FieldLabel, Divider, InputField, ComboField,
    make_btn_primary, make_btn_secondary,
)


# ══════════════════════════════════════════════════════════════════════════════
# Step indicator
# ══════════════════════════════════════════════════════════════════════════════

class StepIndicator(QWidget):
    STEPS = ['Identification', 'Specimen', 'Dimensions', 'Process']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(62)
        self._current = 0
        self.setStyleSheet(f'background: {C_WHITE}; border-bottom: 1px solid {C_BORDER};')

    def set_step(self, idx: int):
        self._current = idx
        self.update()

    def paintEvent(self, event):
        p      = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n      = len(self.STEPS)
        w, h   = self.width(), self.height()
        cell_w = w // n

        for i, label in enumerate(self.STEPS):
            cx   = cell_w * i + cell_w // 2
            cy   = h // 2 - 6
            done = i < self._current
            curr = i == self._current

            # connector line
            if i > 0:
                color = QColor(C_GOLD) if (done or curr) else QColor(C_BORDER)
                p.setPen(QPen(color, 2))
                p.drawLine(cx - cell_w + 18, cy, cx - 18, cy)

            # circle
            if done:
                p.setBrush(QBrush(QColor(C_GOLD)))
                p.setPen(Qt.NoPen)
                p.drawEllipse(cx - 14, cy - 14, 28, 28)
                p.setPen(QPen(QColor('#fff'), 2))
                p.setFont(QFont('Arial', 10, QFont.Bold))
                p.drawText(cx - 14, cy - 14, 28, 28, Qt.AlignCenter, '✓')
            elif curr:
                p.setBrush(QBrush(QColor(C_NAVY)))
                p.setPen(Qt.NoPen)
                p.drawEllipse(cx - 14, cy - 14, 28, 28)
                p.setPen(QPen(QColor('#fff')))
                p.setFont(QFont('Arial', 10, QFont.Bold))
                p.drawText(cx - 14, cy - 14, 28, 28, Qt.AlignCenter, str(i + 1))
            else:
                p.setBrush(QBrush(QColor(C_BG)))
                p.setPen(QPen(QColor(C_BORDER), 2))
                p.drawEllipse(cx - 14, cy - 14, 28, 28)
                p.setPen(QPen(QColor(C_TEXT_LITE)))
                p.setFont(QFont('Arial', 10))
                p.drawText(cx - 14, cy - 14, 28, 28, Qt.AlignCenter, str(i + 1))

            # label
            p.setPen(QPen(QColor(C_NAVY if curr else (C_GOLD if done else C_TEXT_LITE))))
            p.setFont(QFont('Arial', 9, QFont.Bold if curr else QFont.Normal))
            p.drawText(cx - 60, cy + 18, 120, 14, Qt.AlignCenter, label)

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# New Scan wizard
# ══════════════════════════════════════════════════════════════════════════════

class NewScanPage(QWidget):
    """Emits start_camera(dict) when the user finishes all 4 steps."""
    start_camera = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f'background: {C_BG};')

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Step indicator strip
        self.step_ind = StepIndicator()
        root.addWidget(self.step_ind)

        # Scrollable form area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f'background: {C_BG};')

        self.form_stack = QStackedWidget()
        self.form_stack.setStyleSheet(f'background: {C_BG};')

        sc = QWidget(); sc.setStyleSheet(f'background: {C_BG};')
        sc_l = QVBoxLayout(sc)
        sc_l.setContentsMargins(0, 0, 0, 0)
        sc_l.setSpacing(0)
        sc_l.addWidget(self.form_stack)
        sc_l.addStretch()
        scroll.setWidget(sc)
        root.addWidget(scroll, stretch=1)

        # Build each step
        self._build_step0()
        self._build_step1()
        self._build_step2()
        self._build_step3()

        # Bottom nav bar
        nav = QWidget()
        nav.setObjectName('navBar')
        nav.setFixedHeight(72)
        nav.setStyleSheet(
            f'QWidget#navBar {{ background: {C_WHITE}; border-top: 1px solid {C_BORDER}; }}'
            'QWidget#navBar QLabel { border: none; background: transparent; }'
        )
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(24, 12, 24, 12)
        nl.setSpacing(12)

        self.prev_btn    = make_btn_secondary('← Back')
        self.prev_btn.setFixedWidth(120)
        self.prev_btn.clicked.connect(self._prev)

        self.next_btn    = make_btn_primary('Next →')
        self.next_btn.setFixedWidth(140)
        self.next_btn.clicked.connect(self._next)

        self.proceed_btn = make_btn_primary('Open Camera  ▶')
        self.proceed_btn.setFixedWidth(180)
        self.proceed_btn.clicked.connect(self._proceed)

        nl.addWidget(self.prev_btn)
        nl.addStretch()
        nl.addWidget(self.next_btn)
        nl.addWidget(self.proceed_btn)
        root.addWidget(nav)

        self._update_nav()

    # ── Card helper ───────────────────────────────────────────────────────────

    def _card(self, title: str, subtitle: str = ''):
        """Returns (outer_widget, card_layout) for a step's content card."""
        outer = QWidget()
        outer.setStyleSheet(f'background: {C_BG};')
        ol = QVBoxLayout(outer)
        ol.setContentsMargins(24, 16, 24, 16)
        ol.setSpacing(0)

        card = QFrame()
        card.setObjectName('scanCard')
        card.setStyleSheet(
            f'QFrame#scanCard {{ background: {C_WHITE}; border-radius: 14px; '
            f'border: 1px solid {C_BORDER}; }}'
            'QFrame#scanCard QLabel { border: none; background: transparent; }'
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 18, 24, 22)
        cl.setSpacing(12)

        h = QLabel(title)
        h.setStyleSheet(f'color: {C_NAVY}; font-size: 18px; font-weight: 800;')
        cl.addWidget(h)
        if subtitle:
            s = QLabel(subtitle)
            s.setStyleSheet(f'color: {C_TEXT_MID}; font-size: 13px;')
            cl.addWidget(s)
        cl.addWidget(Divider())

        ol.addWidget(card)
        return outer, cl

    def _row(self, layout, label_text: str, widget):
        layout.addWidget(FieldLabel(label_text))
        layout.addWidget(widget)
        layout.addSpacing(6)

    # ── Step 0: Identification ────────────────────────────────────────────────

    def _build_step0(self):
        outer, cl = self._card('Identification', 'Enter specimen and operator details')

        self.sample_id = InputField('e.g. VT-2961')
        self.operator  = InputField('e.g. Rajesh Kumar')

        self.report_id = InputField()
        self.report_id.setReadOnly(True)
        self.report_id.setText(gen_report_id())

        self.scan_date = InputField()
        self.scan_date.setReadOnly(True)
        self.scan_date.setText(now_str())

        self.location = InputField()
        self.location.setReadOnly(True)
        self.location.setText('Welding Bay 3, Plant A — Pune')

        self._row(cl, 'Sample ID *', self.sample_id)
        self._row(cl, 'Operator *', self.operator)

        side = QHBoxLayout(); side.setSpacing(12)
        lc, rc = QVBoxLayout(), QVBoxLayout()
        lc.addWidget(FieldLabel('Report ID'));       lc.addWidget(self.report_id)
        rc.addWidget(FieldLabel('Scan Date & Time')); rc.addWidget(self.scan_date)
        side.addLayout(lc); side.addLayout(rc)
        cl.addLayout(side)

        self._row(cl, 'Location', self.location)
        self.form_stack.addWidget(outer)

    # ── Step 1: Specimen ──────────────────────────────────────────────────────

    def _build_step1(self):
        outer, cl = self._card('Specimen Info', 'Describe the weld specimen')

        self.specimen_type = ComboField()
        self.specimen_type.addItems([
            '', 'Pipe / Cylindrical', 'Plate / Flat',
            'T-Joint', 'Structural Beam', 'Other',
        ])
        self.joint_config = ComboField()
        self.joint_config.addItems([
            '', 'Single V Butt Joint (Plate)', 'Double V Butt Joint',
            'Single U Butt Joint', 'Fillet Weld', 'Lap Joint',
            'Edge Joint', 'Corner Joint',
        ])
        self.material = ComboField()
        self.material.addItems([
            '', 'Stainless Steel', 'Carbon Steel', 'Mild Steel',
            'Aluminium', 'Inconel', 'Duplex Steel', 'Other',
        ])

        self._row(cl, 'Specimen Type *', self.specimen_type)
        self._row(cl, 'Joint Configuration *', self.joint_config)
        self._row(cl, 'Material *', self.material)
        self.form_stack.addWidget(outer)

    # ── Step 2: Dimensions ────────────────────────────────────────────────────
    # Thickness has been removed per design decision.
    # Width and height are plain text inputs (placeholder only — no default value).

    def _build_step2(self):
        outer, cl = self._card('Dimensions', 'Specimen physical dimensions in millimetres')

        self.width_input  = InputField('e.g. 300')
        self.height_input = InputField('e.g. 300')

        side = QHBoxLayout(); side.setSpacing(16)
        wc, hc = QVBoxLayout(), QVBoxLayout()
        wc.addWidget(FieldLabel('Width (mm) *'));  wc.addWidget(self.width_input)
        hc.addWidget(FieldLabel('Height (mm) *')); hc.addWidget(self.height_input)
        side.addLayout(wc); side.addLayout(hc)
        cl.addLayout(side)

        # Live aspect-ratio hint
        self.ratio_lbl = QLabel()
        self.ratio_lbl.setAlignment(Qt.AlignCenter)
        self.ratio_lbl.setStyleSheet(
            f'color: {C_TEXT_MID}; font-size: 12px; border: none; background: transparent;'
        )
        cl.addWidget(self.ratio_lbl)

        def _update_ratio():
            try:
                w = int(self.width_input.text())
                h = int(self.height_input.text())
                if w > 0 and h > 0:
                    g = gcd(w, h)
                    self.ratio_lbl.setText(f'Aspect ratio  {w//g} : {h//g}   ({w} × {h} mm)')
                else:
                    self.ratio_lbl.setText('')
            except ValueError:
                self.ratio_lbl.setText('')

        self.width_input.textChanged.connect(_update_ratio)
        self.height_input.textChanged.connect(_update_ratio)

        self.form_stack.addWidget(outer)

    # ── Step 3: Process ───────────────────────────────────────────────────────

    def _build_step3(self):
        outer, cl = self._card('Process & Industry', 'Welding process and application details')

        self.welding_process = ComboField()
        self.welding_process.addItems([
            '', 'SMAW (Shielded Metal Arc Welding)',
            'GMAW (Gas Metal Arc Welding)', 'GTAW (Gas Tungsten Arc Welding)',
            'FCAW (Flux Cored Arc Welding)', 'SAW (Submerged Arc Welding)', 'Other',
        ])
        self.industry = ComboField()
        self.industry.addItems([
            '', 'Oil & Gas', 'Structural / Construction', 'Power Generation',
            'Automotive', 'Aerospace', 'Shipbuilding', 'Pressure Vessels', 'Other',
        ])
        self.notes = InputField('Optional notes or remarks')

        self._row(cl, 'Welding Process *', self.welding_process)
        self._row(cl, 'Industry / Application *', self.industry)
        self._row(cl, 'Notes', self.notes)
        self.form_stack.addWidget(outer)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _prev(self):
        idx = self.form_stack.currentIndex()
        if idx > 0:
            self.form_stack.setCurrentIndex(idx - 1)
            self._update_nav()

    def _next(self):
        if not self._validate(self.form_stack.currentIndex()):
            return
        idx = self.form_stack.currentIndex()
        if idx < self.form_stack.count() - 1:
            self.form_stack.setCurrentIndex(idx + 1)
            self._update_nav()

    def _update_nav(self):
        idx   = self.form_stack.currentIndex()
        total = self.form_stack.count()
        self.step_ind.set_step(idx)
        self.prev_btn.setVisible(idx > 0)
        self.next_btn.setVisible(idx < total - 1)
        self.proceed_btn.setVisible(idx == total - 1)

    def _validate(self, idx: int) -> bool:
        if idx == 0:
            if not self.sample_id.text().strip():
                self._highlight(self.sample_id, 'Sample ID is required.'); return False
            if not self.operator.text().strip():
                self._highlight(self.operator, 'Operator name is required.'); return False
        elif idx == 1:
            if not self.specimen_type.currentText():
                QMessageBox.warning(self, 'Required', 'Please select a specimen type.'); return False
            if not self.joint_config.currentText():
                QMessageBox.warning(self, 'Required', 'Please select a joint configuration.'); return False
            if not self.material.currentText():
                QMessageBox.warning(self, 'Required', 'Please select a material.'); return False
        elif idx == 2:
            if not self._parse_dim(self.width_input, 'Width'): return False
            if not self._parse_dim(self.height_input, 'Height'): return False
        return True

    def _parse_dim(self, field: InputField, name: str) -> bool:
        try:
            v = int(field.text())
            if v <= 0:
                raise ValueError
            return True
        except ValueError:
            self._highlight(field, f'{name} must be a positive integer.')
            return False

    def _highlight(self, widget, msg: str):
        orig = widget.styleSheet()
        widget.setStyleSheet(orig + ' border-color: #EF4444;')
        QTimer.singleShot(1500, lambda: widget.setStyleSheet(orig))
        QMessageBox.warning(self, 'Required', msg)

    def _proceed(self):
        if not self.welding_process.currentText():
            QMessageBox.warning(self, 'Required', 'Please select a welding process.'); return
        if not self.industry.currentText():
            QMessageBox.warning(self, 'Required', 'Please select an industry.'); return

        data = {
            'sample_id':       self.sample_id.text().strip(),
            'operator':        self.operator.text().strip(),
            'report_id':       self.report_id.text().strip(),
            'scan_date':       self.scan_date.text().strip(),
            'location':        self.location.text().strip(),
            'specimen_type':   self.specimen_type.currentText(),
            'joint_config':    self.joint_config.currentText(),
            'material':        self.material.currentText(),
            'width':           int(self.width_input.text()),
            'height':          int(self.height_input.text()),
            'welding_process': self.welding_process.currentText(),
            'industry':        self.industry.currentText(),
            'notes':           self.notes.text().strip(),
            'scan_number':     gen_scan_number(),
        }
        self.start_camera.emit(data)

    def reset_form(self):
        """Call before showing this page to refresh auto-generated fields."""
        self.report_id.setText(gen_report_id())
        self.scan_date.setText(now_str())
        self.form_stack.setCurrentIndex(0)
        self._update_nav()
