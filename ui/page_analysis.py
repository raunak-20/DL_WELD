"""
ui/page_analysis.py
───────────────────
Analysis page — shown after photo approval.

Frontend-complete pipeline:
  1. Shows the captured (cropped) specimen photo
  2. "Run Analysis" button → simulates AI detection with a spinner
  3. Displays a defect results table (populated from AIService simulation)
  4. "Generate Report" button → calls ReportService, opens PDF viewer

When the real ML model is integrated, replace the simulated DetectionResult
with the real one from AIService.run_inference() — no other changes needed.
"""

import os

from PyQt5.QtCore    import Qt, QTimer, pyqtSignal
from PyQt5.QtGui     import QPixmap, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy, QStackedWidget,
)

from utils.constants import (
    C_NAVY, C_NAVY_DARK, C_GOLD, C_GOLD_DRK, C_BG, C_WHITE, C_BORDER,
    C_TEXT_MID, C_TEXT_LITE, C_GREEN, C_RED, C_AMBER,
)
from utils.widgets import Divider, make_btn_primary, make_btn_secondary, ToastWidget

# Severity → colour map matching the report template
SEV_COLORS = {
    'CRITICAL':    '#C0392B',
    'HIGH':        '#E67E22',
    'MEDIUM':      '#F1C40F',
    'LOW-MEDIUM':  '#F1C40F',
    'LOW':         '#27AE60',
    'PASS':        '#2ECC71',
    'UNKNOWN':     '#9CA3AF',
}


class AnalysisPage(QWidget):
    """
    Emits:
        report_ready(scan_dict, pdf_path) — controller opens the report viewer
    """
    report_ready = pyqtSignal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scan       = {}
        self._ai_result  = None   # DetectionResult, set after analysis runs
        self._report_svc = None   # injected by controller
        self._ai_svc     = None   # injected by controller

        self.setStyleSheet(f'background:{C_BG};')
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # ── Scrollable body ───────────────────────────────────────────────────
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f'background:{C_BG};')

        body = QWidget(); body.setStyleSheet(f'background:{C_BG};')
        self._body_l = QVBoxLayout(body); self._body_l.setContentsMargins(24,20,24,20)
        self._body_l.setSpacing(16)
        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

        # ── Sections (built once, shown/hidden) ───────────────────────────────
        self._sec_photo    = self._build_photo_section()
        self._sec_ready    = self._build_ready_section()
        self._sec_running  = self._build_running_section()
        self._sec_results  = self._build_results_section()

        for sec in [self._sec_photo, self._sec_ready, self._sec_running, self._sec_results]:
            self._body_l.addWidget(sec)
        self._body_l.addStretch()

        # ── Bottom action bar ─────────────────────────────────────────────────
        bar = QWidget(); bar.setObjectName('aBar')
        bar.setFixedHeight(72)
        bar.setStyleSheet(
            f'QWidget#aBar{{background:{C_WHITE};border-top:1px solid {C_BORDER};}}'
            'QWidget#aBar QLabel{border:none;background:transparent;}'
        )
        bl = QHBoxLayout(bar); bl.setContentsMargins(24,12,24,12); bl.setSpacing(12)

        self._run_btn    = make_btn_primary('🔬  Run AI Analysis')
        self._run_btn.setFixedWidth(200)
        self._run_btn.clicked.connect(self._run_analysis)

        self._report_btn = make_btn_primary('📄  Generate Report')
        self._report_btn.setFixedWidth(200)
        self._report_btn.setVisible(False)
        self._report_btn.clicked.connect(self._generate_report)

        bl.addStretch()
        bl.addWidget(self._run_btn)
        bl.addWidget(self._report_btn)
        root.addWidget(bar)

        self.toast = ToastWidget(self)
        self._set_state('ready')   # initial state

    # ── Section builders ──────────────────────────────────────────────────────

    def _card(self, title=''):
        """Returns (outer_widget, card_layout)."""
        outer = QWidget(); outer.setStyleSheet(f'background:{C_BG};')
        ol = QVBoxLayout(outer); ol.setContentsMargins(0,0,0,0); ol.setSpacing(0)
        card = QFrame(); card.setObjectName('aCard')
        card.setStyleSheet(
            f'QFrame#aCard{{background:{C_WHITE};border-radius:12px;border:1px solid {C_BORDER};}}'
            'QFrame#aCard QLabel{border:none;background:transparent;}'
        )
        cl = QVBoxLayout(card); cl.setContentsMargins(20,16,20,18); cl.setSpacing(12)
        if title:
            h = QLabel(title)
            h.setStyleSheet(f'color:{C_NAVY};font-size:15px;font-weight:800;')
            cl.addWidget(h); cl.addWidget(Divider())
        ol.addWidget(card)
        return outer, cl

    def _build_photo_section(self):
        outer, cl = self._card('Captured Specimen')
        self._photo_lbl = QLabel()
        self._photo_lbl.setAlignment(Qt.AlignCenter)
        self._photo_lbl.setFixedHeight(260)
        self._photo_lbl.setStyleSheet('background:#111;border-radius:8px;')
        cl.addWidget(self._photo_lbl)

        self._meta_lbl = QLabel()
        self._meta_lbl.setStyleSheet(f'color:{C_TEXT_MID};font-size:12px;')
        self._meta_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(self._meta_lbl)
        return outer

    def _build_ready_section(self):
        outer, cl = self._card()
        lbl = QLabel('Ready for Analysis')
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f'color:{C_NAVY};font-size:16px;font-weight:700;')
        sub = QLabel('Press "Run AI Analysis" to detect defects in the captured specimen image.')
        sub.setAlignment(Qt.AlignCenter); sub.setWordWrap(True)
        sub.setStyleSheet(f'color:{C_TEXT_MID};font-size:13px;')
        cl.addWidget(lbl); cl.addWidget(sub)
        return outer

    def _build_running_section(self):
        outer, cl = self._card()
        self._spinner_lbl = QLabel('⏳  Running AI inference…')
        self._spinner_lbl.setAlignment(Qt.AlignCenter)
        self._spinner_lbl.setStyleSheet(f'color:{C_NAVY};font-size:15px;font-weight:700;')
        sub = QLabel('Processing image through defect detection model. This may take a moment.')
        sub.setAlignment(Qt.AlignCenter); sub.setWordWrap(True)
        sub.setStyleSheet(f'color:{C_TEXT_MID};font-size:13px;')
        cl.addWidget(self._spinner_lbl); cl.addWidget(sub)
        # Spinner animation (cycles dots)
        self._dot_count = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._tick_spinner)
        return outer

    def _build_results_section(self):
        outer, cl = self._card('Analysis Results')

        # Verdict banner
        self._verdict_banner = QLabel()
        self._verdict_banner.setAlignment(Qt.AlignCenter)
        self._verdict_banner.setFixedHeight(48)
        self._verdict_banner.setStyleSheet(
            f'background:{C_GREEN}22;color:{C_GREEN};font-size:16px;font-weight:800;'
            'border-radius:8px;border:1px solid #22C55E44;'
        )
        cl.addWidget(self._verdict_banner)

        # Stats row
        stats = QHBoxLayout(); stats.setSpacing(10)
        self._stat_widgets = {}
        for key, label in [('defects','Defects Found'),('severity','Max Severity'),('time','Inference Time')]:
            f = QFrame(); f.setObjectName('statF')
            f.setStyleSheet(
                f'QFrame#statF{{background:{C_BG};border-radius:8px;border:1px solid {C_BORDER};}}'
                'QFrame#statF QLabel{border:none;background:transparent;}'
            )
            fl = QVBoxLayout(f); fl.setContentsMargins(12,8,12,8); fl.setSpacing(2)
            v = QLabel('—'); v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(f'color:{C_NAVY};font-size:18px;font-weight:800;')
            k = QLabel(label); k.setAlignment(Qt.AlignCenter)
            k.setStyleSheet(f'color:{C_TEXT_MID};font-size:11px;')
            fl.addWidget(v); fl.addWidget(k)
            self._stat_widgets[key] = v
            stats.addWidget(f)
        cl.addLayout(stats)
        cl.addWidget(Divider())

        # Defect table header
        self._table_container = QWidget()
        self._table_container.setStyleSheet('background:transparent;')
        self._table_l = QVBoxLayout(self._table_container)
        self._table_l.setContentsMargins(0,0,0,0); self._table_l.setSpacing(6)
        cl.addWidget(self._table_container)

        return outer

    # ── State machine ─────────────────────────────────────────────────────────

    def _set_state(self, state: str):
        """States: ready | running | results"""
        self._sec_ready.setVisible(state == 'ready')
        self._sec_running.setVisible(state == 'running')
        self._sec_results.setVisible(state == 'results')
        self._run_btn.setVisible(state in ('ready', 'results'))
        self._report_btn.setVisible(state == 'results')
        self._run_btn.setText('🔬  Run AI Analysis' if state != 'results' else '🔄  Re-run Analysis')
        if state == 'running':
            self._spinner_timer.start(400)
        else:
            self._spinner_timer.stop()

    def _tick_spinner(self):
        self._dot_count = (self._dot_count + 1) % 4
        dots = '.' * self._dot_count
        self._spinner_lbl.setText(f'⏳  Running AI inference{dots}')

    # ── Public API ────────────────────────────────────────────────────────────

    def set_services(self, ai_svc, report_svc):
        """Called by controller to inject services."""
        self._ai_svc     = ai_svc
        self._report_svc = report_svc

    def set_scan(self, sc: dict):
        self._scan      = sc
        self._ai_result = None
        self._set_state('ready')

        # Show photo
        photo = sc.get('photo', '')
        if photo and os.path.exists(photo):
            pm = QPixmap(photo).scaled(560, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._photo_lbl.setPixmap(pm)
        else:
            self._photo_lbl.setText('No image available')
            self._photo_lbl.setStyleSheet(
                f'color:{C_TEXT_LITE};font-size:13px;background:#1a1a1a;border-radius:8px;'
            )

        self._meta_lbl.setText(
            f"Sample: {sc.get('sample_id','—')}  ·  "
            f"Report: {sc.get('report_id','—')}  ·  "
            f"Operator: {sc.get('operator','—')}  ·  "
            f"Date: {sc.get('scan_date','—')}"
        )

    # ── Analysis ──────────────────────────────────────────────────────────────

    def _run_analysis(self):
        self._set_state('running')
        # Simulate async delay (replace with real inference call if needed)
        QTimer.singleShot(1800, self._finish_analysis)

    def _finish_analysis(self):
        # Run AI service (simulation until real model is plugged in)
        if self._ai_svc:
            # Try to load the captured frame for inference
            try:
                import cv2
                photo = self._scan.get('photo', '')
                frame = cv2.imread(photo) if photo and os.path.exists(photo) else None
            except Exception:
                frame = None
            self._ai_result = self._ai_svc.run_inference(frame)
        else:
            self._ai_result = None

        self._populate_results()
        self._set_state('results')

    def _populate_results(self):
        result = self._ai_result

        # Clear old table rows
        while self._table_l.count():
            item = self._table_l.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        boxes   = getattr(result, 'boxes', [])
        t_ms    = getattr(result, 'inference_time_ms', 0)
        simulated = getattr(result, 'is_simulated', True)

        if not boxes:
            verdict = 'PASS — No Defects Detected'
            v_style = f'background:{C_GREEN}22;color:{C_GREEN};font-size:16px;font-weight:800;border-radius:8px;border:1px solid #22C55E44;'
            self._stat_widgets['defects'].setText('0')
            self._stat_widgets['severity'].setText('—')
        else:
            verdict = f'DEFECTS DETECTED — {len(boxes)} Instance{"s" if len(boxes)>1 else ""}'
            v_style = f'background:{C_RED}22;color:{C_RED};font-size:16px;font-weight:800;border-radius:8px;border:1px solid #EF444444;'
            self._stat_widgets['defects'].setText(str(len(boxes)))
            self._stat_widgets['severity'].setText(self._max_severity(boxes))

        if simulated:
            verdict += '  ⚡ (Simulated)'
        self._verdict_banner.setText(verdict)
        self._verdict_banner.setStyleSheet(v_style)
        self._stat_widgets['time'].setText(f'{t_ms:.0f} ms')

        # Update scan dict for report
        self._scan['overall_verdict'] = 'DEFECTS DETECTED' if boxes else 'PASS'
        self._scan['confidence_avg']  = (
            round(sum(b.confidence for b in boxes) / len(boxes) * 100, 1) if boxes else 0.0
        )

        if boxes:
            # Table header
            hdr = self._table_row(
                ['#', 'Defect Type', 'Confidence', 'Severity'],
                is_header=True
            )
            self._table_l.addWidget(hdr)

            # Group by label
            groups: dict[str, list] = {}
            for b in boxes:
                groups.setdefault(b.label, []).append(b)

            for i, (label, blist) in enumerate(
                sorted(groups.items(), key=lambda x: -sum(b.confidence for b in x[1])/len(x[1])), 1
            ):
                avg_conf = sum(b.confidence for b in blist) / len(blist)
                sev = self._severity_for_label(label)
                sev_color = SEV_COLORS.get(sev, '#9CA3AF')
                row_w = self._table_row([
                    str(i),
                    label.replace('_',' ').title(),
                    f'{avg_conf*100:.1f}%',
                    sev,
                ], row_idx=i, sev_color=sev_color if i == 4 else None, sev_col_idx=3)
                self._table_l.addWidget(row_w)
        else:
            ok = QLabel('✓  No defects detected — weld meets visual acceptance criteria.')
            ok.setStyleSheet(
                f'color:{C_GREEN};font-size:13px;font-weight:600;'
                'border:none;background:transparent;padding:8px 0;'
            )
            self._table_l.addWidget(ok)

    def _table_row(self, cells: list, is_header=False, row_idx=0, sev_color=None, sev_col_idx=None):
        row = QWidget()
        row.setObjectName('trow')
        bg = C_NAVY if is_header else (C_WHITE if row_idx % 2 == 1 else C_BG)
        row.setStyleSheet(
            f'QWidget#trow{{background:{bg};border-radius:6px;}}'
            'QWidget#trow QLabel{border:none;background:transparent;}'
        )
        rl = QHBoxLayout(row); rl.setContentsMargins(12,7,12,7); rl.setSpacing(0)
        col_widths = [0.06, 0.40, 0.24, 0.30]
        for ci, (cell, cw) in enumerate(zip(cells, col_widths)):
            lbl = QLabel(str(cell))
            if is_header:
                lbl.setStyleSheet('color:#fff;font-size:11px;font-weight:700;')
            elif ci == sev_col_idx and sev_color:
                lbl.setStyleSheet(
                    f'color:{sev_color};font-size:12px;font-weight:700;'
                )
            else:
                lbl.setStyleSheet(f'color:{C_NAVY};font-size:12px;font-weight:{"600" if ci==1 else "400"};')
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            rl.addWidget(lbl, int(cw * 100))
        return row

    # ── Report generation ─────────────────────────────────────────────────────

    def _generate_report(self):
        if not self._report_svc:
            self.toast.show_toast('Report service not available','⚠',C_AMBER); return

        self._report_btn.setText('⏳  Generating…')
        self._report_btn.setEnabled(False)

        def _do():
            try:
                path = self._report_svc.generate(self._scan, self._ai_result)
                self._report_btn.setText('📄  Generate Report')
                self._report_btn.setEnabled(True)
                self.report_ready.emit(self._scan, path)
            except Exception as e:
                self._report_btn.setText('📄  Generate Report')
                self._report_btn.setEnabled(True)
                self.toast.show_toast(f'Report error: {e}','✗',C_RED,5000)

        QTimer.singleShot(100, _do)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _max_severity(self, boxes) -> str:
        order = ['CRITICAL','HIGH','MEDIUM','LOW-MEDIUM','LOW','UNKNOWN']
        sevs  = [self._severity_for_label(b.label) for b in boxes]
        for s in order:
            if s in sevs: return s
        return 'UNKNOWN'

    @staticmethod
    def _severity_for_label(label: str) -> str:
        mapping = {
            'crack':              'CRITICAL',
            'lack_of_fusion':     'CRITICAL',
            'incomplete_fusion':  'CRITICAL',
            'lack_of_penetration':'HIGH',
            'burn_through':       'HIGH',
            'slag_inclusion':     'HIGH',
            'excess_reinforcement': 'HIGH',
            'undercut':           'MEDIUM',
            'porosity':           'MEDIUM',
            'overlap':            'MEDIUM',
            'underfill':          'MEDIUM',
            'arc_strike':         'LOW-MEDIUM',
            'spatter':            'LOW',
            'spatters':           'LOW',
            'mechanical_mark':    'LOW',
        }
        return mapping.get(label.lower(), 'UNKNOWN')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.toast._reposition()
